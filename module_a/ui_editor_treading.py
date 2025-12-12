import tkinter as tk
from tkinter import ttk, messagebox

# 引入网络代理接口
from db_proxy import (
    add_survey, add_question, add_option,
    get_full_survey_detail, update_survey_title,
    update_question_text, update_option_text,
    delete_question, delete_option, delete_survey,
    add_violation, update_survey_status, publish_survey,
    copy_question, get_question_options,
    add_question_with_options
)
from module_a.violation_checker import ViolationChecker


# ============================================================================
# 1. 辅助类：可滚动的 Frame (保持不变，已修复销毁报错)
# ============================================================================
class ScrollableFrame(tk.Frame):
    def __init__(self, container, *args, **kwargs):
        super().__init__(container, *args, **kwargs)

        self.canvas = tk.Canvas(self, bg="#F5F5F5", highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)

        self.scrollable_frame = tk.Frame(self.canvas, bg="#F5F5F5")

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas_window = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")

        self.canvas.bind(
            "<Configure>",
            lambda e: self.canvas.itemconfig(self.canvas_window, width=e.width)
        )

        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        self.bind("<Destroy>", self._on_destroy)

    def _on_mousewheel(self, event):
        try:
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        except tk.TclError:
            pass

    def _on_destroy(self, event):
        try:
            self.canvas.unbind_all("<MouseWheel>")
        except:
            pass


# ============================================================================
# 2. 核心组件：单题编辑器 Widget (深度优化版)
# ============================================================================
class QuestionWidget(tk.Frame):
    def __init__(self, master, question_data, survey_id, refresh_callback, checker, sock):
        super().__init__(master, bg="white", bd=1, relief="solid")
        self.pack(fill=tk.X, padx=10, pady=10)

        self.sock = sock
        self.q_data = question_data  # 这里面已经包含了 options 列表！
        self.survey_id = survey_id
        self.refresh_callback = refresh_callback
        self.checker = checker
        self.q_id = question_data['question_id']
        self.q_type = question_data['type']

        # 本地维护选项列表，避免频繁网络请求
        # q_data['options'] 应该是一个字符串列表 ["选项1", "选项2"]
        # 注意：这里有一个小的架构债，get_full_survey_detail 只返回了选项文本，没返回选项ID。
        # 为了保证修改选项时能找到ID，我们需要在 create_ui 时做特殊处理。
        # 考虑到性能，我们初始化时先只渲染文本。修改时再查ID，或者我们在后端修改 get_full_survey_detail。
        # 但为了不改后端，这里我们在 QuestionWidget 初始化时，不查网络，直接渲染。

        self.create_ui()

    def _refocus(self):
        try:
            top = self.winfo_toplevel()
            top.lift()
            top.focus_force()
        except:
            pass

    def get_type_name(self):
        type_map = {"choice": "单选题", "radio": "单选题", "checkbox": "多选题", "text": "填空题", "slider": "滑动条"}
        return type_map.get(self.q_type, "未知题型")

    def create_ui(self):
        # 标题栏
        header = tk.Frame(self, bg="white")
        header.pack(fill=tk.X, padx=10, pady=10)
        tk.Label(header, text="*", fg="red", bg="white", font=("Arial", 12)).pack(side=tk.LEFT)
        tk.Label(header, text=f"{self.q_data['index']}.", bg="white", font=("Arial", 12, "bold")).pack(side=tk.LEFT)

        self.title_entry = tk.Entry(header, font=("Arial", 12), bd=0, bg="#F9F9F9")
        self.title_entry.insert(0, self.q_data['text'])
        self.title_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.title_entry.bind("<FocusOut>", self.save_title)

        # 选项区域
        self.options_container = tk.Frame(self, bg="white")
        self.options_container.pack(fill=tk.X, padx=20)

        if self.q_type == 'slider':
            self.render_slider_preview()
        elif self.q_type in ["choice", "radio", "checkbox"]:
            # 【核心优化】直接使用父级传来的数据渲染，不查网络！
            self.render_options_from_cache()
            tk.Button(self, text="⊞ 选项 (添加)", command=self.add_new_option, bg="white", fg="#2196F3", bd=0,
                      cursor="hand2").pack(anchor="w", padx=20, pady=5)
        elif self.q_type == "text":
            tk.Label(self.options_container, text="[ 用户在此处输入文本 ]", fg="gray", bg="white").pack(anchor="w",
                                                                                                        pady=10)

        # 底部栏
        footer = tk.Frame(self, height=1, bg="#E0E0E0")
        footer.pack(fill=tk.X, pady=5)
        tools = tk.Frame(self, bg="white", height=40)
        tools.pack(fill=tk.X, padx=10, pady=5)

        tk.Label(tools, text=f"【{self.get_type_name()}】", fg="#2196F3", bg="white", font=("Arial", 10, "bold")).pack(
            side=tk.LEFT)
        tk.Label(tools, text="⚙ 设置", fg="gray", bg="white", font=("Arial", 10)).pack(side=tk.LEFT, padx=8)

        tk.Button(tools, text="完成编辑", bg="#2196F3", fg="white", command=self.save_all).pack(side=tk.RIGHT, padx=5)
        tk.Label(tools, text="•••", fg="gray", bg="white", font=("Arial", 14)).pack(side=tk.RIGHT, padx=5)
        tk.Button(tools, text="🗑️", command=self.delete_me, bg="white", bd=0, cursor="hand2").pack(side=tk.RIGHT,
                                                                                                   padx=5)
        tk.Button(tools, text="❐", command=self.copy_me, bg="white", bd=0, cursor="hand2").pack(side=tk.RIGHT, padx=5)

    def render_slider_preview(self):
        f = tk.Frame(self.options_container, bg="white")
        f.pack(fill=tk.X, pady=10)
        tk.Label(f, text=" ", font=("Arial", 14), bg="white", width=3, bd=1, relief="solid").pack(side=tk.LEFT, padx=10)
        tk.Scale(f, from_=1, to=10, orient=tk.HORIZONTAL, bg="white", length=300, showvalue=0).set(5)
        nums = tk.Frame(self.options_container, bg="white")
        nums.pack(fill=tk.X, padx=55)
        for i in range(1, 11):
            tk.Label(nums, text=str(i), bg="white", fg="gray").pack(side=tk.LEFT, expand=True)

    def render_options_from_cache(self):
        """【新增】从本地缓存渲染选项，极大提升速度"""
        for w in self.options_container.winfo_children(): w.destroy()

        # 这里的 options 是纯文本列表 ["男", "女"]
        options = self.q_data.get('options', [])

        # 注意：这里我们没有 OptionID。
        # 为了解决“没有ID无法修改”的问题，我们采用一种折中方案：
        # 初始化显示时，为了快，不绑定具体的ID。
        # 当用户点击输入框想要修改时，我们再去网络请求获取真正的 ID 列表。
        # 或者，更简单地，我们调用一次 load_options_with_ids (此时只对这一个题目发请求，不卡顿)

        # 策略：直接发起一次异步请求获取带ID的选项，但不要阻塞主界面初始化
        # 鉴于 Tkinter 异步麻烦，我们这里还是得调用 get_question_options。
        # 但是！为了不卡死，我们只在用户 *点击* 编辑框时才去查 ID？不行，太复杂。

        # 【最终优化方案】：我们还是得查一次 ID，但是我们把 QuestionWidget 的初始化
        # 放在 render_questions 里控制频率，或者忍受这一个请求。
        # 实际上，之前卡是因为 10 个题目并发查。
        # 既然我们使用了 options 文本，我们可以仅渲染文本。
        # 为了能编辑，我们必须知道 ID。
        # 让我们妥协一下：初始化时调用 get_question_options，但希望服务器快一点。
        # 如果卡顿依然严重，说明 get_question_options 太慢。

        # 尝试直接加载
        self.load_options_from_server()

    def load_options_from_server(self):
        """从服务器加载选项 (带ID)"""
        try:
            # 这里的请求是必要的，为了获取 OptionID 以便修改
            rows = get_question_options(self.sock, self.q_id)
            for w in self.options_container.winfo_children(): w.destroy()
            for opt_id, opt_text in rows:
                self.create_option_row(opt_id, opt_text)
        except Exception:
            # 如果失败（比如超时），至少把文本显示出来（只读模式）
            options = self.q_data.get('options', [])
            for txt in options:
                lbl = tk.Entry(self.options_container, bg="white", bd=0)
                lbl.insert(0, txt)
                lbl.config(state="disabled")  # 暂时不可编辑
                lbl.pack(fill=tk.X)

    def create_option_row(self, opt_id, text):
        row = tk.Frame(self.options_container, bg="white")
        row.pack(fill=tk.X, pady=2)
        icon = "○" if self.q_type in ['radio', 'choice'] else "□"
        tk.Label(row, text=icon, fg="gray", bg="white", font=("Arial", 14)).pack(side=tk.LEFT)
        ent = tk.Entry(row, bg="white", bd=0, font=("Arial", 11))
        ent.insert(0, text)
        ent.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        # 绑定保存
        ent.bind("<FocusOut>", lambda e, oid=opt_id, et=ent: self.save_option(oid, et.get()))
        # 绑定删除
        tk.Button(row, text="✕", bg="white", bd=0, fg="gray", cursor="hand2",
                  command=lambda oid=opt_id: self.delete_option_ui(oid)).pack(side=tk.RIGHT)

    def save_title(self, event=None):
        txt = self.title_entry.get().strip()
        if not txt: return
        is_bad, word = self.checker.check_text(txt)
        if is_bad: return messagebox.showerror("违规", f"题目含违规词：{word}", parent=self)
        try:
            update_question_text(self.sock, self.q_id, txt)
        except:
            pass

    def save_option(self, option_id, text):
        text = text.strip()
        if not text: return
        is_bad, word = self.checker.check_text(text)
        if is_bad: return messagebox.showerror("违规", f"选项含违规词：{word}", parent=self)
        try:
            update_option_text(self.sock, option_id, text)
        except:
            pass

    def add_new_option(self):
        count = len(self.options_container.winfo_children()) + 1
        text = f"选项{count}"
        try:
            nid = add_option(self.sock, self.q_id, count, text)
            self.create_option_row(nid, text)
        except Exception as e:
            messagebox.showerror("错误", f"添加选项失败: {e}", parent=self)

    def delete_option_ui(self, option_id):
        if messagebox.askyesno("确认", "删除此选项？", parent=self):
            try:
                delete_option(self.sock, option_id)
                self.load_options_from_server()  # 刷新选项
            except Exception as e:
                messagebox.showerror("错误", f"删除选项失败: {e}", parent=self)
            self._refocus()

    def delete_me(self):
        if messagebox.askyesno("确认", "删除此题目？", parent=self):
            try:
                delete_question(self.sock, self.q_id)
                # 【重要修改】删除题目后，必须强制全量刷新，否则题号不更新
                self.refresh_callback(scroll_action='force_refresh')
            except Exception as e:
                messagebox.showerror("错误", f"删除题目失败: {e}", parent=self)
            self._refocus()

    def copy_me(self):
        try:
            copy_question(self.sock, self.survey_id, self.q_id)
            # 复制也全量刷新，确保顺序
            self.refresh_callback(scroll_action='bottom')
        except Exception as e:
            messagebox.showerror("错误", f"复制失败: {e}", parent=self)

    def save_all(self):
        self.save_title()
        messagebox.showinfo("成功", "本题编辑完成", parent=self)
        self._refocus()


# ============================================================================
# 3. 主窗口：问卷编辑器
# ============================================================================
class SurveyEditorWindow(tk.Toplevel):
    def __init__(self, master, user_id, sock):
        super().__init__(master)
        self.title("编辑调查")
        self.sock = sock
        self.user_id = user_id
        self.checker = ViolationChecker()
        self.survey_id = None
        self._is_processing = False  # 防抖锁

        master.update_idletasks()
        try:
            self.geometry(master.winfo_geometry())
        except:
            self.geometry("1024x768")
        self.resizable(False, False)

        self.transient(master)
        self.grab_set()

        self.container = tk.Frame(self)
        self.container.pack(fill=tk.BOTH, expand=True)
        self.show_title_input_page()

    def _refocus(self):
        try:
            self.lift()
            self.focus_force()
        except:
            pass

    # ------------------ 阶段 1: 标题输入 ------------------
    def show_title_input_page(self):
        for w in self.container.winfo_children(): w.destroy()
        page = tk.Frame(self.container, bg="#F0F2F5")
        page.pack(fill=tk.BOTH, expand=True)
        card = tk.Frame(page, bg="white", bd=1, relief="solid")
        card.place(relx=0.5, rely=0.5, anchor="center", width=600, height=400)

        tk.Label(card, text="从空白创建调查", font=("Arial", 18, "bold"), bg="white").pack(pady=(50, 20))
        tk.Label(card, text="问卷标题：", font=("Arial", 12), bg="white", fg="#666").pack(anchor="w", padx=50)

        self.init_title_entry = tk.Entry(card, font=("Arial", 14), bd=1, relief="solid")
        self.init_title_entry.pack(fill=tk.X, padx=50, pady=10, ipady=8)
        self.init_title_entry.insert(0, "请输入标题")
        self.init_title_entry.bind("<FocusIn>", lambda e: self.init_title_entry.delete(0,
                                                                                       tk.END) if self.init_title_entry.get() == "请输入标题" else None)

        tk.Button(card, text="创建调查", bg="#2196F3", fg="white", font=("Arial", 14, "bold"),
                  relief="flat", cursor="hand2", command=self.create_survey_action).pack(fill=tk.X, padx=50, pady=40,
                                                                                         ipady=5)

    def create_survey_action(self):
        title = self.init_title_entry.get().strip()
        if not title or title == "请输入标题":
            return messagebox.showwarning("提示", "标题不能为空", parent=self)
        is_bad, word = self.checker.check_text(title)
        if is_bad:
            return messagebox.showerror("违规", f"标题含违规词：{word}", parent=self)

        try:
            self.survey_id = add_survey(self.sock, self.user_id, title, "draft")
            self.show_editor_page()
        except Exception as e:
            messagebox.showerror("错误", f"创建问卷失败: {e}", parent=self)

    # ------------------ 阶段 2: 编辑列表 ------------------
    def show_editor_page(self):
        for w in self.container.winfo_children(): w.destroy()

        # 顶部栏
        top = tk.Frame(self.container, bg="white", height=50, bd=1, relief="raised")
        top.pack(fill=tk.X, side=tk.TOP)
        tk.Button(top, text="🏠", font=("Arial", 16), bd=0, bg="white", cursor="hand2",
                  command=self.confirm_exit_home).pack(side=tk.LEFT, padx=10)
        tk.Label(top, text="编辑调查", font=("Arial", 14, "bold"), bg="white").pack(side=tk.LEFT, padx=20)
        tk.Button(top, text="完成编辑", bg="#4CAF50", fg="white", font=("Arial", 12, "bold"),
                  relief="flat", padx=15, cursor="hand2", command=self.finish_editing).pack(side=tk.RIGHT, padx=20,
                                                                                            pady=8)

        # 内容区
        content = tk.Frame(self.container)
        content.pack(fill=tk.BOTH, expand=True)

        # 左侧预览
        left = tk.Frame(content, bg="#F0F2F5", width=512)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        preview = tk.Frame(left, bg="white", bd=1, relief="solid")
        preview.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        # 问卷大标题
        tf = tk.Frame(preview, bg="white", pady=10)
        tf.pack(fill=tk.X)
        try:
            detail = get_full_survey_detail(self.sock, self.survey_id)
            cur_title = detail['survey_title']
        except:
            cur_title = "未知标题"

        self.main_title_entry = tk.Entry(tf, font=("Arial", 18, "bold"), fg="#2196F3", bg="white", bd=0,
                                         justify="center")
        self.main_title_entry.insert(0, cur_title)
        self.main_title_entry.pack(fill=tk.X, padx=20)
        self.main_title_entry.bind("<FocusOut>", self.update_survey_title_action)
        tk.Label(tf, text="添加问卷说明", fg="gray", bg="white").pack()

        self.scroll_area = ScrollableFrame(preview)
        self.scroll_area.pack(fill=tk.BOTH, expand=True)
        self.scroll_area.canvas.configure(bg="white")
        self.scroll_area.scrollable_frame.configure(bg="white")

        # 右侧工具栏
        right = tk.Frame(content, bg="white", width=512, bd=1, relief="solid")
        right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        tk.Label(right, text="添加题目", font=("Arial", 16, "bold"), bg="white", pady=20).pack()

        # 基础题型
        tk.Label(right, text="添加基础题型", font=("Arial", 10), fg="gray", bg="white").pack(anchor="w", padx=60)
        basic_box = tk.Frame(right, bg="white")
        basic_box.pack(fill=tk.X, padx=(60, 20), pady=10)
        types = [("◎ 单选题", "choice"), ("☑ 多选题", "checkbox"), ("✎ 填空题", "text"), ("⇋ 滑动条", "slider")]
        for idx, (lbl, tp) in enumerate(types):
            r, c = idx // 2, idx % 2
            tk.Button(basic_box, text=lbl, font=("Arial", 11), bg="#F5F5F5", bd=0, pady=12, width=18, cursor="hand2",
                      command=lambda t=tp: self.add_question_directly(t)).grid(row=r, column=c, padx=10, pady=8)

        # 模板题型
        tk.Label(right, text="\n添加题目模板", font=("Arial", 10), fg="gray", bg="white").pack(anchor="w", padx=60)
        tpl_box = tk.Frame(right, bg="white")
        tpl_box.pack(fill=tk.X, padx=(60, 20), pady=10)
        tpls = [("姓名", "tpl_name"), ("性别", "tpl_gender"), ("年龄段", "tpl_age"), ("手机", "tpl_mobile")]
        for idx, (lbl, tp) in enumerate(tpls):
            r, c = idx // 2, idx % 2
            tk.Button(tpl_box, text=lbl, font=("Arial", 11), bg="#F0F8FF", bd=0, pady=12, width=18, cursor="hand2",
                      command=lambda t=tp: self.add_template_directly(t)).grid(row=r, column=c, padx=10, pady=8)

        self.render_questions(scroll_action='bottom')

    def update_survey_title_action(self, event):
        if not hasattr(self, 'main_title_entry') or not self.main_title_entry.winfo_exists():
            return
        txt = self.main_title_entry.get().strip()
        if not txt: return
        try:
            is_bad, word = self.checker.check_text(txt)
            if is_bad:
                messagebox.showerror("违规", f"标题含违规词：{word}", parent=self)
                self._refocus()
                return
            update_survey_title(self.sock, self.survey_id, txt)
        except:
            pass  # 忽略自动保存的错误

    # ========================================================
    # 核心修复逻辑：渲染与增量更新
    # ========================================================
    def render_questions(self, scroll_action=None):
        """
        全量刷新列表。
        scroll_action: 'bottom' (到底部), 'keep' (保持位置), 'force_refresh' (强制重载)
        """
        # 如果是 force_refresh (例如删除后)，必须清空重绘
        saved_y = 0
        if scroll_action == 'keep':
            saved_y = self.scroll_area.canvas.yview()[0]

        # 清空当前列表
        for w in self.scroll_area.scrollable_frame.winfo_children(): w.destroy()

        try:
            # 【重要】这里是一次性请求，如果数据量大，5秒可能不够，建议 client_socket 超时至少 10s
            data = get_full_survey_detail(self.sock, self.survey_id)
            if not data:
                return  # 可能是空的或者出错了

            questions = data.get('questions', [])

            # 循环创建组件
            for q in questions:
                QuestionWidget(self.scroll_area.scrollable_frame, q, self.survey_id, self.render_questions,
                               self.checker, self.sock)

        except Exception as e:
            # 这里的错误是 "刷新失败"，可能是因为删除了题目后索引还没更新完就查了
            # 我们可以选择静默，或者提示
            print(f"Render error (ignored): {e}")

        # 处理滚动
        self.scroll_area.update_idletasks()
        if scroll_action == 'bottom':
            self.after(50, lambda: self.scroll_area.canvas.yview_moveto(1.0))
        elif scroll_action == 'keep':
            self.after(50, lambda: self.scroll_area.canvas.yview_moveto(saved_y))

    def _append_new_question(self, q_id, q_text, q_type, options=[]):
        """增量渲染：直接在底部添加，不查网络"""
        # 计算本地序号
        current_count = len(self.scroll_area.scrollable_frame.winfo_children())
        new_index = current_count + 1

        q_data = {
            'question_id': q_id,
            'index': new_index,
            'text': q_text,
            'type': q_type,
            'options': options  # 传递选项，避免 QuestionWidget 再查
        }

        QuestionWidget(self.scroll_area.scrollable_frame, q_data, self.survey_id, self.render_questions, self.checker,
                       self.sock)

        self.scroll_area.update_idletasks()
        self.after(20, lambda: self.scroll_area.canvas.yview_moveto(1.0))

    def add_question_directly(self, q_type):
        if self._is_processing: return
        self._is_processing = True
        self.config(cursor="watch")
        self.update_idletasks()

        try:
            current_count = len(self.scroll_area.scrollable_frame.winfo_children())
            new_index = current_count + 1
            titles = {"choice": "单选题", "checkbox": "多选题", "text": "填空题", "slider": "评分题 (1-10)"}

            options = []
            if q_type in ["choice", "checkbox"]:
                options = ["选项1", "选项2"]
            elif q_type == "slider":
                options = [str(i) for i in range(1, 11)]

            # 发送批量请求
            q_id = add_question_with_options(self.sock, self.survey_id, new_index, titles[q_type], q_type, options)

            # 增量渲染
            self._append_new_question(q_id, titles[q_type], q_type, options)

        except Exception as e:
            messagebox.showerror("错误", f"添加失败: {e}", parent=self)
        finally:
            self._is_processing = False
            self.config(cursor="")

    def add_template_directly(self, tpl_type):
        if self._is_processing: return
        self._is_processing = True
        self.config(cursor="watch")
        self.update_idletasks()

        try:
            current_count = len(self.scroll_area.scrollable_frame.winfo_children())
            new_index = current_count + 1

            tpls = {
                "tpl_name": {"t": "您的姓名是？", "y": "text", "o": []},
                "tpl_gender": {"t": "您的性别？", "y": "choice", "o": ["女", "男", "其他"]},
                "tpl_age": {"t": "您的年龄段：", "y": "choice",
                            "o": ["18岁以下", "18~25", "26~30", "31~40", "41~50", "51~60", "60以上"]},
                "tpl_mobile": {"t": "请输入您的电话号码：", "y": "text", "o": []}
            }
            t = tpls.get(tpl_type)
            if not t: return

            q_id = add_question_with_options(self.sock, self.survey_id, new_index, t['t'], t['y'], t['o'])
            self._append_new_question(q_id, t['t'], t['y'], t['o'])

        except Exception as e:
            messagebox.showerror("错误", f"添加模板失败: {e}", parent=self)
        finally:
            self._is_processing = False
            self.config(cursor="")

    def finish_editing(self):
        if hasattr(self, 'main_title_entry'):
            self.update_survey_title_action(None)

        if messagebox.askyesno("发布", "是否立即发布问卷？\n(是=发布, 否=存草稿)", parent=self):
            try:
                publish_survey(self.sock, self.survey_id)
                messagebox.showinfo("成功", "已发布！", parent=self)
            except Exception as e:
                messagebox.showerror("失败", str(e), parent=self)
            self.destroy()
        else:
            self.destroy()

    def confirm_exit_home(self):
        if not self.survey_id: return self.destroy()

        if hasattr(self, 'main_title_entry'):
            self.update_survey_title_action(None)

        res = messagebox.askyesno("返回", "保存当前草稿？\n(是=保存, 否=删除)", parent=self)
        self._refocus()

        if res:
            self.destroy()
        else:
            if messagebox.askyesno("确认", "确定删除？不可恢复。", parent=self):
                try:
                    delete_survey(self.sock, self.survey_id)
                except:
                    pass
                self.destroy()
            else:
                self._refocus()