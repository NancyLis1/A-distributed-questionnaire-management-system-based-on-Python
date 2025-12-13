import tkinter as tk
from tkinter import ttk, messagebox
import threading
import socket

# 引入配置
from module_b.client_socket import SERVER_HOST, SERVER_PORT

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
# 1. 辅助类：可滚动的 Frame
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
# 2. 核心组件：单题编辑器 Widget
# ============================================================================
class QuestionWidget(tk.Frame):
    def __init__(self, master, question_data, survey_id, refresh_callback, checker, sock, append_callback=None):
        super().__init__(master, bg="white", bd=1, relief="solid")
        self.pack(fill=tk.X, padx=10, pady=10)

        self.sock = sock
        self.q_data = question_data
        self.survey_id = survey_id
        self.refresh_callback = refresh_callback
        self.append_callback = append_callback
        self.checker = checker
        self.q_id = question_data['question_id']
        self.q_type = question_data['type']

        self.index_label = None
        self.create_ui()

    def _refocus(self):
        try:
            if self.winfo_toplevel().winfo_exists():
                top = self.winfo_toplevel()
                top.lift()
                top.focus_force()
        except:
            pass

    def get_type_name(self):
        type_map = {"choice": "单选题", "radio": "单选题", "checkbox": "多选题", "text": "填空题", "slider": "滑动条"}
        return type_map.get(self.q_type, "未知题型")

    def update_index_label(self, new_index):
        if self.index_label and self.winfo_exists():
            self.index_label.config(text=f"{new_index}.")
        self.q_data['index'] = new_index

    def run_thread(self, target_func, callback=None):
        def worker():
            try:
                res = target_func()
                if callback:
                    self.after(0, lambda: callback(res))
            except Exception as e:
                print(f"[Bg Error]: {e}")

        threading.Thread(target=worker, daemon=True).start()

    def create_ui(self):
        header = tk.Frame(self, bg="white")
        header.pack(fill=tk.X, padx=10, pady=10)
        tk.Label(header, text="*", fg="red", bg="white", font=("Arial", 12)).pack(side=tk.LEFT)

        self.index_label = tk.Label(header, text=f"{self.q_data['index']}.", bg="white", font=("Arial", 12, "bold"))
        self.index_label.pack(side=tk.LEFT)

        self.title_entry = tk.Entry(header, font=("Arial", 12), bd=0, bg="#F9F9F9")
        self.title_entry.insert(0, self.q_data['text'])
        self.title_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.title_entry.bind("<FocusOut>", self.save_title)

        self.options_container = tk.Frame(self, bg="white")
        self.options_container.pack(fill=tk.X, padx=20)

        if self.q_type == 'slider':
            self.render_slider_preview()
        elif self.q_type in ["choice", "radio", "checkbox"]:
            if 'options' in self.q_data and self.q_data['options']:
                for opt_text in self.q_data['options']:
                    self.create_option_row(None, opt_text)
                # 后台同步 ID
                self.load_options_async()
            else:
                self.load_options_async()

            tk.Button(self, text="⊞ 选项 (添加)", command=self.add_new_option, bg="white", fg="#2196F3", bd=0,
                      cursor="hand2").pack(anchor="w", padx=20, pady=5)
        elif self.q_type == "text":
            tk.Label(self.options_container, text="[ 用户在此处输入文本 ]", fg="gray", bg="white").pack(anchor="w",
                                                                                                        pady=10)

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

    def load_options_async(self):
        def fetch():
            return get_question_options(self.sock, self.q_id)

        def update_ui(rows):
            if not self.winfo_exists(): return
            if not rows or not isinstance(rows, list): return

            for w in self.options_container.winfo_children(): w.destroy()
            for opt_id, opt_text in rows:
                self.create_option_row(opt_id, opt_text)

        self.run_thread(fetch, update_ui)

    def create_option_row(self, opt_id, text):
        row = tk.Frame(self.options_container, bg="white")
        row.pack(fill=tk.X, pady=2)
        icon = "○" if self.q_type in ['radio', 'choice'] else "□"
        tk.Label(row, text=icon, fg="gray", bg="white", font=("Arial", 14)).pack(side=tk.LEFT)
        ent = tk.Entry(row, bg="white", bd=0, font=("Arial", 11))
        ent.insert(0, text)
        ent.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        cmd = lambda: self.delete_option_ui(opt_id, row)
        if opt_id:
            ent.bind("<FocusOut>", lambda e, oid=opt_id, et=ent: self.save_option(oid, et.get()))

        tk.Button(row, text="✕", bg="white", bd=0, fg="gray", cursor="hand2", command=cmd).pack(side=tk.RIGHT)

    def save_title(self, event=None):
        txt = self.title_entry.get().strip()
        if not txt: return
        is_bad, word = self.checker.check_text(txt)
        if is_bad: return messagebox.showerror("违规", f"题目含违规词：{word}", parent=self)
        self.run_thread(lambda: update_question_text(self.sock, self.q_id, txt))

    def save_option(self, option_id, text):
        text = text.strip()
        if not text: return
        is_bad, word = self.checker.check_text(text)
        if is_bad: return messagebox.showerror("违规", f"选项含违规词：{word}", parent=self)
        self.run_thread(lambda: update_option_text(self.sock, option_id, text))

    def add_new_option(self):
        count = len(self.options_container.winfo_children()) + 1
        text = f"选项{count}"

        def task():
            return add_option(self.sock, self.q_id, count, text)

        def done(nid):
            if self.winfo_exists():
                self.create_option_row(nid, text)

        self.run_thread(task, done)

    def delete_option_ui(self, option_id, row_widget):
        if messagebox.askyesno("确认", "删除此选项？", parent=self):
            row_widget.destroy()
            if option_id:
                def task(): delete_option(self.sock, option_id)

                self.run_thread(task)
            self._refocus()

    def delete_me(self):
        if messagebox.askyesno("确认", "删除此题目？", parent=self):
            # 乐观UI：立即移除
            self.refresh_callback(scroll_action='delete', target_widget=self)

            def task():
                try:
                    delete_question(self.sock, self.q_id)
                except:
                    pass

            threading.Thread(target=task, daemon=True).start()

    def copy_me(self):
        txt = self.title_entry.get()
        opts = []
        if self.q_type in ["choice", "checkbox"]:
            for child in self.options_container.winfo_children():
                for widget in child.winfo_children():
                    if isinstance(widget, tk.Entry):
                        opts.append(widget.get())
        elif self.q_type == "slider":
            opts = [str(i) for i in range(1, 11)]

        if self.append_callback:
            self.append_callback(txt, self.q_type, opts)

    def save_all(self):
        self.save_title()
        messagebox.showinfo("成功", "本题编辑完成", parent=self)
        self._refocus()


# ============================================================================
# 3. 主窗口：问卷编辑器 (增加模态加载遮罩)
# ============================================================================
class SurveyEditorWindow(tk.Toplevel):
    def __init__(self, master, user_id, sock=None):
        super().__init__(master)
        self.title("编辑调查")

        # 建立独立连接
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((SERVER_HOST, SERVER_PORT))
        except Exception as e:
            messagebox.showerror("连接错误", f"无法连接服务器: {e}")
            self.destroy()
            return

        self.user_id = user_id
        self.checker = ViolationChecker()
        self.survey_id = None
        self.loading_overlay = None  # 遮罩层

        master.update_idletasks()
        try:
            self.geometry(master.winfo_geometry())
        except:
            self.geometry("1024x768")
        self.resizable(False, False)

        self.transient(master)
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        self.container = tk.Frame(self)
        self.container.pack(fill=tk.BOTH, expand=True)
        self.show_title_input_page()

        # 预热
        threading.Thread(target=lambda: get_question_options(self.sock, -1), daemon=True).start()

    def on_close(self):
        try:
            self.sock.close()
        except:
            pass
        self.destroy()

    def _refocus(self):
        try:
            self.lift()
            self.focus_force()
        except:
            pass

    # =====================================================
    # 核心新增：模态加载遮罩 (锁住鼠标)
    # =====================================================
    def show_loading(self, message="正在处理..."):
        """显示全屏遮罩，阻止用户操作"""
        if self.loading_overlay and self.loading_overlay.winfo_exists():
            return

        self.loading_overlay = tk.Toplevel(self)
        self.loading_overlay.transient(self)
        # grab_set 确保鼠标无法点击编辑器其他区域
        self.loading_overlay.grab_set()
        self.loading_overlay.wm_overrideredirect(True)  # 无边框

        # 居中显示
        try:
            w, h = 300, 100
            x = self.winfo_x() + (self.winfo_width() // 2) - (w // 2)
            y = self.winfo_y() + (self.winfo_height() // 2) - (h // 2)
            self.loading_overlay.geometry(f"{w}x{h}+{x}+{y}")
        except:
            self.loading_overlay.geometry("300x100+200+200")

        frame = tk.Frame(self.loading_overlay, bg="#333333", bd=2, relief="raised")
        frame.pack(fill=tk.BOTH, expand=True)
        tk.Label(frame, text="⏳ " + message, fg="white", bg="#333333", font=("Arial", 12)).pack(expand=True)
        self.update_idletasks()

    def hide_loading(self):
        """移除遮罩"""
        if self.loading_overlay and self.loading_overlay.winfo_exists():
            self.loading_overlay.grab_release()
            self.loading_overlay.destroy()
            self.loading_overlay = None

    def run_thread(self, target_func, callback=None, error_callback=None):
        def worker():
            try:
                res = target_func()
                if callback:
                    self.after(0, lambda: callback(res))
            except Exception as e:
                err = e
                if error_callback:
                    self.after(0, lambda: error_callback(err))
                else:
                    print(f"Async Error: {err}")

        threading.Thread(target=worker, daemon=True).start()

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

        # 开启遮罩，锁住鼠标
        self.show_loading("正在创建问卷...")

        def task():
            return add_survey(self.sock, self.user_id, title, "draft")

        def done(sid):
            self.survey_id = sid
            self.hide_loading()
            self.show_editor_page()

        def fail(e):
            self.hide_loading()
            # 友好提示
            if "超时" in str(e):
                messagebox.showwarning("提示", "网络响应稍慢，请稍后重试。")
            else:
                messagebox.showerror("错误", f"创建失败: {e}", parent=self)

        self.run_thread(task, done, fail)

    # ------------------ 阶段 2: 编辑列表 ------------------
    def show_editor_page(self):
        # 先清除旧界面
        for w in self.container.winfo_children(): w.destroy()

        # 显示遮罩，异步加载详情
        self.show_loading("加载数据中...")

        def fetch_data():
            # 在后台线程一次性获取所有数据
            return get_full_survey_detail(self.sock, self.survey_id)

        def build_ui(detail):
            self.hide_loading()  # 数据回来了，取消遮罩
            self._build_editor_layout(detail)  # 构建界面

        self.run_thread(fetch_data, build_ui)

    def _build_editor_layout(self, detail):
        """实际构建编辑页面的 UI"""
        top = tk.Frame(self.container, bg="white", height=50, bd=1, relief="raised")
        top.pack(fill=tk.X, side=tk.TOP)
        tk.Button(top, text="🏠", font=("Arial", 16), bd=0, bg="white", cursor="hand2",
                  command=self.confirm_exit_home).pack(side=tk.LEFT, padx=10)
        tk.Label(top, text="编辑调查", font=("Arial", 14, "bold"), bg="white").pack(side=tk.LEFT, padx=20)
        tk.Button(top, text="完成编辑", bg="#4CAF50", fg="white", font=("Arial", 12, "bold"),
                  relief="flat", padx=15, cursor="hand2", command=self.finish_editing).pack(side=tk.RIGHT, padx=20,
                                                                                            pady=8)

        content = tk.Frame(self.container)
        content.pack(fill=tk.BOTH, expand=True)

        left = tk.Frame(content, bg="#F0F2F5", width=512)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        preview = tk.Frame(left, bg="white", bd=1, relief="solid")
        preview.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        tf = tk.Frame(preview, bg="white", pady=10)
        tf.pack(fill=tk.X)

        cur_title = detail['survey_title'] if detail else "问卷标题"
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

        right = tk.Frame(content, bg="white", width=512, bd=1, relief="solid")
        right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        tk.Label(right, text="添加题目", font=("Arial", 16, "bold"), bg="white", pady=20).pack()

        tk.Label(right, text="添加基础题型", font=("Arial", 10), fg="gray", bg="white").pack(anchor="w", padx=60)
        basic_box = tk.Frame(right, bg="white")
        basic_box.pack(fill=tk.X, padx=(60, 20), pady=10)
        types = [("◎ 单选题", "choice"), ("☑ 多选题", "checkbox"), ("✎ 填空题", "text"), ("⇋ 滑动条", "slider")]
        for idx, (lbl, tp) in enumerate(types):
            r, c = idx // 2, idx % 2
            tk.Button(basic_box, text=lbl, font=("Arial", 11), bg="#F5F5F5", bd=0, pady=12, width=18, cursor="hand2",
                      command=lambda t=tp: self.add_question_directly(t)).grid(row=r, column=c, padx=10, pady=8)

        tk.Label(right, text="\n添加题目模板", font=("Arial", 10), fg="gray", bg="white").pack(anchor="w", padx=60)
        tpl_box = tk.Frame(right, bg="white")
        tpl_box.pack(fill=tk.X, padx=(60, 20), pady=10)
        tpls = [("姓名", "tpl_name"), ("性别", "tpl_gender"), ("年龄段", "tpl_age"), ("手机", "tpl_mobile")]
        for idx, (lbl, tp) in enumerate(tpls):
            r, c = idx // 2, idx % 2
            tk.Button(tpl_box, text=lbl, font=("Arial", 11), bg="#F0F8FF", bd=0, pady=12, width=18, cursor="hand2",
                      command=lambda t=tp: self.add_template_directly(t)).grid(row=r, column=c, padx=10, pady=8)

        # 初始渲染题目
        questions = detail.get('questions', []) if detail else []
        for q in questions:
            QuestionWidget(self.scroll_area.scrollable_frame, q, self.survey_id, self.render_questions, self.checker,
                           self.sock, self.add_question_internal)

    def update_survey_title_action(self, event):
        if not hasattr(self, 'main_title_entry') or not self.main_title_entry.winfo_exists(): return
        txt = self.main_title_entry.get().strip()
        if not txt: return
        is_bad, word = self.checker.check_text(txt)
        if is_bad:
            messagebox.showerror("违规", f"标题含违规词：{word}", parent=self)
            return

        threading.Thread(target=lambda: update_survey_title(self.sock, self.survey_id, txt), daemon=True).start()

    def render_questions(self, scroll_action=None, target_widget=None):
        if scroll_action == 'delete' and target_widget:
            target_widget.destroy()
            self.scroll_area.update_idletasks()
            widgets = self.scroll_area.scrollable_frame.winfo_children()
            for i, w in enumerate(widgets):
                if isinstance(w, QuestionWidget):
                    w.update_index_label(i + 1)
            return

        saved_y = 0
        if scroll_action == 'keep':
            saved_y = self.scroll_area.canvas.yview()[0]

        # 全量刷新也加遮罩，防止乱点
        self.show_loading("同步数据中...")

        def fetch():
            d = get_full_survey_detail(self.sock, self.survey_id)
            return d.get('questions', []) if d else []

        def draw(questions):
            self.hide_loading()  # 取消遮罩
            for w in self.scroll_area.scrollable_frame.winfo_children(): w.destroy()

            for q in questions:
                QuestionWidget(self.scroll_area.scrollable_frame, q, self.survey_id, self.render_questions,
                               self.checker, self.sock, self.add_question_internal)

            self.scroll_area.update_idletasks()
            if scroll_action == 'bottom':
                self.after(20, lambda: self.scroll_area.canvas.yview_moveto(1.0))
            elif scroll_action == 'keep':
                self.after(20, lambda: self.scroll_area.canvas.yview_moveto(saved_y))

        self.run_thread(fetch, draw)

    def _append_new_question(self, q_id, q_text, q_type, options=[]):
        current_count = len(self.scroll_area.scrollable_frame.winfo_children())
        new_index = current_count + 1

        q_data = {
            'question_id': q_id,
            'index': new_index,
            'text': q_text,
            'type': q_type,
            'options': options
        }

        QuestionWidget(self.scroll_area.scrollable_frame, q_data, self.survey_id, self.render_questions, self.checker,
                       self.sock, self.add_question_internal)
        self.scroll_area.update_idletasks()
        self.after(20, lambda: self.scroll_area.canvas.yview_moveto(1.0))

    def add_question_internal(self, text, q_type, options):
        # 开启遮罩，防止连点
        self.show_loading("添加中...")

        current_count = len(self.scroll_area.scrollable_frame.winfo_children())
        new_index = current_count + 1

        def bg_task():
            return add_question_with_options(self.sock, self.survey_id, new_index, text, q_type, options)

        def done(qid):
            self.hide_loading()
            self._append_new_question(qid, text, q_type, options)

        def fail(e):
            self.hide_loading()
            # 失败则全量刷新回滚
            print(f"Add failed: {e}, syncing UI...")
            self.render_questions(scroll_action='bottom')

        self.run_thread(bg_task, done, fail)

    def add_question_directly(self, q_type):
        titles = {"choice": "单选题", "checkbox": "多选题", "text": "填空题", "slider": "评分题 (1-10)"}
        options = [str(i) for i in range(1, 11)] if q_type == "slider" else (
            ["选项1", "选项2"] if q_type in ["choice", "checkbox"] else [])
        self.add_question_internal(titles[q_type], q_type, options)

    def add_template_directly(self, tpl_type):
        tpls = {
            "tpl_name": {"t": "您的姓名是？", "y": "text", "o": []},
            "tpl_gender": {"t": "您的性别？", "y": "choice", "o": ["女", "男", "其他"]},
            "tpl_age": {"t": "您的年龄段：", "y": "choice",
                        "o": ["18岁以下", "18~25", "26~30", "31~40", "41~50", "51~60", "60以上"]},
            "tpl_mobile": {"t": "请输入您的电话号码：", "y": "text", "o": []}
        }
        t = tpls.get(tpl_type)
        if t:
            self.add_question_internal(t['t'], t['y'], t['o'])

    def finish_editing(self):
        if hasattr(self, 'main_title_entry'):
            # 主线程获取标题
            title = self.main_title_entry.get().strip()
        else:
            title = None

        if messagebox.askyesno("发布", "是否立即发布问卷？\n(是=发布, 否=存草稿)", parent=self):
            # 开启遮罩，防止误触
            self.show_loading("发布中...")

            def task():
                if title:
                    update_survey_title(self.sock, self.survey_id, title)
                publish_survey(self.sock, self.survey_id)

            def done(_):
                self.hide_loading()
                messagebox.showinfo("成功", "已发布！", parent=self)
                self.destroy()

            def fail(e):
                self.hide_loading()
                if "超时" in str(e):
                    messagebox.showwarning("超时", "请求已发送，请刷新列表查看。", parent=self)
                    self.destroy()
                else:
                    messagebox.showerror("失败", str(e), parent=self)

            self.run_thread(task, done, fail)
        else:
            self.destroy()

    def confirm_exit_home(self):
        if not self.survey_id: return self.destroy()

        title = None
        if hasattr(self, 'main_title_entry'):
            title = self.main_title_entry.get().strip()

        res = messagebox.askyesno("返回", "保存当前草稿？\n(是=保存, 否=删除)", parent=self)
        self._refocus()

        if res:
            if title:
                threading.Thread(target=lambda: update_survey_title(self.sock, self.survey_id, title),
                                 daemon=True).start()
            self.destroy()
        else:
            if messagebox.askyesno("确认", "确定删除？不可恢复。", parent=self):
                def task():
                    try:
                        delete_survey(self.sock, self.survey_id)
                    except:
                        pass

                def done(_):
                    self.destroy()

                self.run_thread(task, done, done)
            else:
                self._refocus()