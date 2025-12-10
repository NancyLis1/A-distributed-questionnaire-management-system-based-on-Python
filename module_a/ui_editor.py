import tkinter as tk
from tkinter import ttk, messagebox

# 引入后端接口 (已移除 sqlite3，新增 copy_question 和 get_question_options)
from db_utils import (
    add_survey, add_question, add_option,
    get_full_survey_detail, update_survey_title,
    update_question_text, update_option_text,
    delete_question, delete_option, delete_survey,
    add_violation, update_survey_status, publish_survey,
    copy_question, get_question_options  # <--- 新增的两个接口
)
# 引入违规检测
from module_a.violation_checker import ViolationChecker


# ============================================================================
# 1. 辅助类：可滚动的 Frame (ScrollableFrame)
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

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")


# ============================================================================
# 2. 核心组件：单题编辑器 Widget (QuestionWidget)
# ============================================================================
class QuestionWidget(tk.Frame):
    def __init__(self, master, question_data, survey_id, refresh_callback, checker):
        super().__init__(master, bg="white", bd=1, relief="solid")
        self.pack(fill=tk.X, padx=10, pady=10)

        self.q_data = question_data
        self.survey_id = survey_id
        self.refresh_callback = refresh_callback
        self.checker = checker
        self.q_id = question_data['question_id']
        self.q_type = question_data['type']

        self.create_ui()

    def _refocus(self):
        """辅助方法：强制拉回顶层焦点"""
        top = self.winfo_toplevel()
        top.lift()
        top.focus_force()

    def get_type_name(self):
        """获取题型的中文显示名称"""
        type_map = {
            "choice": "单选题",
            "radio": "单选题",
            "checkbox": "多选题",
            "text": "填空题",
            "slider": "滑动条"
        }
        return type_map.get(self.q_type, "未知题型")

    def create_ui(self):
        # --- 第一行：标题编辑区 ---
        header_frame = tk.Frame(self, bg="white")
        header_frame.pack(fill=tk.X, padx=10, pady=10)

        tk.Label(header_frame, text="*", fg="red", bg="white", font=("Arial", 12)).pack(side=tk.LEFT)

        idx_text = f"{self.q_data['index']}."
        tk.Label(header_frame, text=idx_text, bg="white", font=("Arial", 12, "bold")).pack(side=tk.LEFT)

        self.title_entry = tk.Entry(header_frame, font=("Arial", 12), bd=0, bg="#F9F9F9")
        self.title_entry.insert(0, self.q_data['text'])
        self.title_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.title_entry.bind("<FocusOut>", self.save_title)

        # --- 第二行：选项/内容区域 ---
        self.options_container = tk.Frame(self, bg="white")
        self.options_container.pack(fill=tk.X, padx=20)

        # 处理滑动条 (slider)
        if self.q_type == 'slider':
            self.render_slider_preview()

        # 处理普通选择题
        elif self.q_type in ["choice", "radio", "checkbox"]:
            self.load_options()
            add_opt_btn = tk.Button(self, text="⊞ 选项 (添加)", command=self.add_new_option,
                                    bg="white", fg="#2196F3", bd=0, cursor="hand2")
            add_opt_btn.pack(anchor="w", padx=20, pady=5)

        # 处理填空题
        elif self.q_type == "text":
            tk.Label(self.options_container, text="[ 用户在此处输入文本 ]", fg="gray", bg="white").pack(anchor="w",
                                                                                                        pady=10)

        # --- 第三行：底部工具栏 ---
        tk.Frame(self, height=1, bg="#E0E0E0").pack(fill=tk.X, pady=5)
        tool_frame = tk.Frame(self, bg="white", height=40)
        tool_frame.pack(fill=tk.X, padx=10, pady=5)

        # 显示中文题型标签
        tk.Label(tool_frame, text=f"【{self.get_type_name()}】", fg="#2196F3", bg="white",
                 font=("Arial", 10, "bold")).pack(side=tk.LEFT)
        tk.Label(tool_frame, text="⚙ 设置", fg="gray", bg="white", font=("Arial", 10)).pack(side=tk.LEFT, padx=8)

        tk.Button(tool_frame, text="完成编辑", bg="#2196F3", fg="white", command=self.save_all).pack(side=tk.RIGHT,
                                                                                                     padx=5)
        tk.Label(tool_frame, text="•••", fg="gray", bg="white", font=("Arial", 14)).pack(side=tk.RIGHT, padx=5)
        tk.Button(tool_frame, text="🗑️", command=self.delete_me, bg="white", bd=0, cursor="hand2").pack(side=tk.RIGHT,
                                                                                                        padx=5)
        tk.Button(tool_frame, text="❐", command=self.copy_me, bg="white", bd=0, cursor="hand2").pack(side=tk.RIGHT,
                                                                                                     padx=5)

    def render_slider_preview(self):
        # 模拟显示一个 1-10 的滑动条
        frame = tk.Frame(self.options_container, bg="white")
        frame.pack(fill=tk.X, pady=10)

        val_label = tk.Label(frame, text=" ", font=("Arial", 14, "bold"), bg="white", width=3, bd=1, relief="solid")
        val_label.pack(side=tk.LEFT, padx=10)

        scale = tk.Scale(frame, from_=1, to=10, orient=tk.HORIZONTAL,
                         bg="white", length=300, highlightthickness=0, showvalue=0)
        scale.set(5)
        scale.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10)

        scale_nums = tk.Frame(self.options_container, bg="white")
        scale_nums.pack(fill=tk.X, padx=55)
        for i in range(1, 11):
            tk.Label(scale_nums, text=str(i), bg="white", fg="gray").pack(side=tk.LEFT, expand=True)

    def load_options(self):
        """【修改】不再直接连接数据库，而是调用 db_utils"""
        for widget in self.options_container.winfo_children():
            widget.destroy()

        # 调用接口获取 (id, text) 列表
        rows = get_question_options(self.q_id)

        for opt_id, opt_text in rows:
            self.create_option_row(opt_id, opt_text)

    def create_option_row(self, opt_id, text):
        row = tk.Frame(self.options_container, bg="white")
        row.pack(fill=tk.X, pady=2)

        icon = "○" if self.q_type in ['radio', 'choice'] else "□"
        tk.Label(row, text=icon, fg="gray", bg="white", font=("Arial", 14)).pack(side=tk.LEFT)

        entry = tk.Entry(row, bg="white", bd=0, font=("Arial", 11))
        entry.insert(0, text)
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        entry.bind("<FocusOut>", lambda e, oid=opt_id, ent=entry: self.save_option(oid, ent.get()))

        del_btn = tk.Button(row, text="✕", bg="white", bd=0, fg="gray", cursor="hand2",
                            command=lambda oid=opt_id: self.delete_option_ui(oid))
        del_btn.pack(side=tk.RIGHT)

    def save_title(self, event=None):
        new_text = self.title_entry.get().strip()
        if not new_text:
            messagebox.showwarning("提示", "题目不能为空", parent=self)
            self._refocus()
            return

        is_v, word = self.checker.check_text(new_text)
        if is_v:
            messagebox.showerror("违规", f"题目包含违规词：{word}", parent=self)
            self._refocus()
            return

        update_question_text(self.q_id, new_text)

    def save_option(self, option_id, new_text):
        new_text = new_text.strip()
        if not new_text: return
        is_v, word = self.checker.check_text(new_text)
        if is_v:
            messagebox.showerror("违规", f"选项包含违规词：{word}", parent=self)
            self._refocus()
            return
        update_option_text(option_id, new_text)

    def add_new_option(self):
        count = len(self.options_container.winfo_children()) + 1
        text = f"选项{count}"
        new_id = add_option(self.q_id, count, text)
        self.create_option_row(new_id, text)

    def delete_option_ui(self, option_id):
        if messagebox.askyesno("确认", "是否确认删除该选项？", parent=self):
            delete_option(option_id)
            self.load_options()
            self._refocus()
        else:
            self._refocus()

    def delete_me(self):
        if messagebox.askyesno("确认", "是否确认删除该题目？此操作不可逆。", parent=self):
            delete_question(self.q_id)
            self.refresh_callback(scroll_action='keep')
            self._refocus()
        else:
            self._refocus()

    def copy_me(self):
        """【修改】不再手动写 SQL，调用封装好的 copy_question"""
        try:
            copy_question(self.survey_id, self.q_id)
            self.refresh_callback(scroll_action='bottom')
        except Exception as e:
            messagebox.showerror("错误", f"复制失败: {str(e)}", parent=self)
            self._refocus()

    def save_all(self):
        self.save_title()
        messagebox.showinfo("成功", "本题编辑已完成", parent=self)
        self._refocus()


# ============================================================================
# 3. 主窗口类：问卷编辑器 (SurveyEditorWindow)
# ============================================================================
class SurveyEditorWindow(tk.Toplevel):
    def __init__(self, master, user_id):
        super().__init__(master)
        self.title("编辑调查")

        master.update_idletasks()
        try:
            geom = master.winfo_geometry()
            self.geometry(geom)
        except:
            self.geometry("1024x768")

        self.resizable(False, False)

        self.user_id = user_id
        self.checker = ViolationChecker()
        self.survey_id = None

        self.transient(master)
        self.grab_set()

        self.container = tk.Frame(self)
        self.container.pack(fill=tk.BOTH, expand=True)

        self.show_title_input_page()

    def _refocus(self):
        self.lift()
        self.focus_force()

    # ------------------------------------------------------------------------
    # 阶段 1: 标题输入页
    # ------------------------------------------------------------------------
    def show_title_input_page(self):
        for widget in self.container.winfo_children():
            widget.destroy()

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

        btn = tk.Button(card, text="创建调查", bg="#2196F3", fg="white", font=("Arial", 14, "bold"),
                        relief="flat", cursor="hand2", command=self.create_survey_action)
        btn.pack(fill=tk.X, padx=50, pady=40, ipady=5)

    def create_survey_action(self):
        title = self.init_title_entry.get().strip()

        if not title or title == "请输入标题":
            messagebox.showwarning("提示", "标题不能为空", parent=self)
            self._refocus()
            return

        is_v, word = self.checker.check_text(title)
        if is_v:
            messagebox.showerror("违规", f"标题包含违规词：{word}", parent=self)
            self._refocus()
            return

        self.survey_id = add_survey(self.user_id, title, "draft")
        self.show_editor_page()

    # ------------------------------------------------------------------------
    # 阶段 2: 编辑列表页
    # ------------------------------------------------------------------------
    def show_editor_page(self):
        for widget in self.container.winfo_children():
            widget.destroy()

        # === 顶部导航栏 ===
        top_bar = tk.Frame(self.container, bg="white", height=50, bd=1, relief="raised")
        top_bar.pack(fill=tk.X, side=tk.TOP)

        home_btn = tk.Button(top_bar, text="🏠", font=("Arial", 16), bd=0, bg="white", cursor="hand2",
                             command=self.confirm_exit_home)
        home_btn.pack(side=tk.LEFT, padx=10, pady=5)

        tk.Label(top_bar, text="编辑调查", font=("Arial", 14, "bold"), bg="white").pack(side=tk.LEFT, padx=20)

        finish_btn = tk.Button(top_bar, text="完成编辑", bg="#4CAF50", fg="white",
                               font=("Arial", 12, "bold"), relief="flat", padx=15,
                               cursor="hand2", command=self.finish_editing)
        finish_btn.pack(side=tk.RIGHT, padx=20, pady=8)

        # === 主体分栏 (Left 50%, Right 50%) ===
        main_content = tk.Frame(self.container)
        main_content.pack(fill=tk.BOTH, expand=True)

        # --- 左侧：问卷预览 (50%) ---
        left_panel = tk.Frame(main_content, bg="#F0F2F5", width=512)
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        preview_container = tk.Frame(left_panel, bg="white", bd=1, relief="solid")
        preview_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        title_frame = tk.Frame(preview_container, bg="white", pady=10)
        title_frame.pack(fill=tk.X)

        detail = get_full_survey_detail(self.survey_id)
        current_title = detail['survey_title']

        self.main_title_entry = tk.Entry(title_frame, font=("Arial", 18, "bold"), fg="#2196F3",
                                         bg="white", bd=0, justify="center")
        self.main_title_entry.insert(0, current_title)
        self.main_title_entry.pack(fill=tk.X, padx=20)
        self.main_title_entry.bind("<FocusOut>", self.update_survey_title_action)
        tk.Label(title_frame, text="添加问卷说明", fg="gray", bg="white").pack()

        self.scroll_area = ScrollableFrame(preview_container)
        self.scroll_area.pack(fill=tk.BOTH, expand=True)
        self.scroll_area.canvas.configure(bg="white")
        self.scroll_area.scrollable_frame.configure(bg="white")

        # --- 右侧：固定工具栏 (50%) ---
        right_panel = tk.Frame(main_content, bg="white", width=512, bd=1, relief="solid")
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # 顶部标题
        tk.Label(right_panel, text="添加题目", font=("Arial", 16, "bold"), bg="white", pady=20).pack()

        # >>> 修改部分：使用 Grid 布局 + 增大按钮 + 右移容器 <<<

        # 1. 基础题型
        tk.Label(right_panel, text="添加基础题型", font=("Arial", 10), fg="gray", bg="white").pack(anchor="w",
                                                                                                   padx=60)  # 标签也稍微右移

        # 容器 padx=(60, 20)：左边留60像素，右边留20像素，实现整体右移视觉效果
        basic_frame = tk.Frame(right_panel, bg="white")
        basic_frame.pack(fill=tk.X, padx=(60, 20), pady=10)

        basic_types = [
            ("◎ 单选题", "choice"), ("☑ 多选题", "checkbox"),
            ("✎ 填空题", "text"), ("⇋ 滑动条", "slider")
        ]

        for idx, (label, q_type) in enumerate(basic_types):
            row = idx // 2
            col = idx % 2

            btn = tk.Button(basic_frame, text=label, font=("Arial", 11), bg="#F5F5F5", bd=0,
                            pady=12, width=18, cursor="hand2",
                            command=lambda t=q_type: self.add_question_directly(t))
            # 增加 grid 的 padx/pady，让按钮之间更宽松
            btn.grid(row=row, column=col, padx=10, pady=8)

        # 2. 模板题型
        tk.Label(right_panel, text="\n添加题目模板", font=("Arial", 10), fg="gray", bg="white").pack(anchor="w",
                                                                                                     padx=60)

        tpl_frame = tk.Frame(right_panel, bg="white")
        tpl_frame.pack(fill=tk.X, padx=(60, 20), pady=10)

        templates = [
            ("姓名", "tpl_name"), ("性别", "tpl_gender"),
            ("年龄段", "tpl_age"), ("手机", "tpl_mobile")
        ]

        for idx, (label, tpl_type) in enumerate(templates):
            row = idx // 2
            col = idx % 2
            btn = tk.Button(tpl_frame, text=label, font=("Arial", 11), bg="#F0F8FF", bd=0,
                            pady=12, width=18, cursor="hand2",
                            command=lambda t=tpl_type: self.add_template_directly(t))
            btn.grid(row=row, column=col, padx=10, pady=8)

        self.render_questions()

    # ------------------------------------------------------------------------
    # 逻辑操作
    # ------------------------------------------------------------------------
    def update_survey_title_action(self, event):
        new_title = self.main_title_entry.get().strip()
        if not new_title:
            messagebox.showwarning("提示", "标题不能为空", parent=self)
            self._refocus()
            return

        is_v, word = self.checker.check_text(new_title)
        if is_v:
            messagebox.showerror("违规", f"标题包含违规词：{word}", parent=self)
            self._refocus()
            return

        update_survey_title(self.survey_id, new_title)

    def render_questions(self, scroll_action=None):
        saved_y = 0
        if scroll_action == 'keep':
            saved_y = self.scroll_area.canvas.yview()[0]

        for widget in self.scroll_area.scrollable_frame.winfo_children():
            widget.destroy()

        data = get_full_survey_detail(self.survey_id)
        questions = data.get('questions', [])

        for q in questions:
            QuestionWidget(self.scroll_area.scrollable_frame, q, self.survey_id, self.render_questions, self.checker)

        if scroll_action == 'bottom':
            self.scroll_area.update_idletasks()
            self.after(50, lambda: self.scroll_area.canvas.yview_moveto(1.0))
        elif scroll_action == 'keep':
            self.scroll_area.update_idletasks()
            self.after(50, lambda: self.scroll_area.canvas.yview_moveto(saved_y))

    def add_question_directly(self, q_type):
        """直接添加题目"""
        data = get_full_survey_detail(self.survey_id)
        new_index = len(data['questions']) + 1

        # 1. 在字典里增加 slider 的默认标题
        default_titles = {
            "choice": "单选题",
            "checkbox": "多选题",
            "text": "填空题",
            "slider": "评分题 (1-10)"  # <--- 新增默认标题
        }

        # 2. 插入问题 (数据库中 type 字段将被存为 'slider')
        q_id = add_question(self.survey_id, new_index, default_titles[q_type], q_type)

        # 3. 处理选项逻辑
        if q_type in ["choice", "checkbox"]:
            # 普通选择题：默认给两个选项
            add_option(q_id, 1, "选项1")
            add_option(q_id, 2, "选项2")

        elif q_type == "slider":
            # 【核心修改】滑动条：自动生成 1 到 10 的选项
            # 这样成员 B 获取 get_full_survey_detail 时，options 列表里就是 ["1", "2", ..., "10"]
            for i in range(1, 11):
                add_option(q_id, i, str(i))

        self.render_questions(scroll_action='bottom')

    def add_template_directly(self, tpl_type):
        data = get_full_survey_detail(self.survey_id)
        new_index = len(data['questions']) + 1

        templates = {
            "tpl_name": {
                "title": "您的姓名是？", "type": "text", "options": []
            },
            "tpl_gender": {
                "title": "您的性别？", "type": "choice", "options": ["女", "男", "其他"]
            },
            "tpl_age": {
                "title": "您的年龄段：", "type": "choice",
                "options": ["18岁以下", "18~25", "26~30", "31~40", "41~50", "51~60", "60以上"]
            },
            "tpl_mobile": {
                "title": "请输入您的电话号码：", "type": "text", "options": []
            }
        }

        tpl = templates.get(tpl_type)
        if not tpl: return

        q_id = add_question(self.survey_id, new_index, tpl['title'], tpl['type'])

        for idx, opt_text in enumerate(tpl['options'], 1):
            add_option(q_id, idx, opt_text)

        self.render_questions(scroll_action='bottom')

    def finish_editing(self):
        self.update_survey_title_action(None)

        if messagebox.askyesno("发布问卷", "是否将问卷立即发布？\n（是：发布，否：保存为草稿）",
                               parent=self):
            try:
                publish_survey(self.survey_id)
                messagebox.showinfo("成功", "问卷已发布！", parent=self)
            except Exception as e:
                messagebox.showerror("错误", f"发布失败: {str(e)}", parent=self)
            self.destroy()
        else:
            messagebox.showinfo("已保存", "问卷已保存为草稿。", parent=self)
            self.destroy()

    def confirm_exit_home(self):
        if self.survey_id is None:
            self.destroy()
            return

        res = messagebox.askyesno("返回", "是否将当前问卷存为草稿？\n（是：保存；否：不保存并删除）", parent=self)
        self._refocus()

        if res:
            self.update_survey_title_action(None)
            self.destroy()
        else:
            if messagebox.askyesno("二次确认", "确定不保存并删除问卷？此操作不可逆。", parent=self):
                delete_survey(self.survey_id)
                self.destroy()
            else:
                self._refocus()