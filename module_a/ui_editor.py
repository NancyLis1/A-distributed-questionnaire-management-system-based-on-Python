import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from datetime import datetime

# 引入后端接口
from db_utils import (
    add_survey, add_question, add_option,
    get_full_survey_detail, update_survey_title,
    update_question_text, update_option_text,
    delete_question, delete_option, delete_survey,
    add_violation  # 用于记录违规
)
# 引入违规检测
from module_a.violation_checker import ViolationChecker


# ============================================================================
# 1. 辅助类：可滚动的 Frame (ScrollableFrame)
# 用于实现题目过多时的上下滑动效果
# ============================================================================
# module_a/ui_editor.py 中的 ScrollableFrame 类

class ScrollableFrame(tk.Frame):
    def __init__(self, container, *args, **kwargs):
        super().__init__(container, *args, **kwargs)

        self.canvas = tk.Canvas(self, bg="#F5F5F5", highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)

        self.scrollable_frame = tk.Frame(self.canvas, bg="#F5F5F5")

        # 1. 监听内部 Frame 大小变化，更新滚动区域
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        # 2. 【关键修改】创建 window 时记录 ID，并设置 anchor='nw'
        self.canvas_window = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")

        # 3. 【关键修改】监听 Canvas 大小变化，强制内部 Frame 宽度与 Canvas 一致
        self.canvas.bind(
            "<Configure>",
            lambda e: self.canvas.itemconfig(self.canvas_window, width=e.width)
        )

        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

    # _on_mousewheel 方法保持不变
    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")


# ============================================================================
# 2. 核心组件：单题编辑器 Widget (QuestionWidget)
# 对应你图片中“红色框框”的部分，每个题目都是这样一个对象
# ============================================================================
class QuestionWidget(tk.Frame):
    def __init__(self, master, question_data, survey_id, refresh_callback):
        """
        :param master: 父容器 (ScrollableFrame)
        :param question_data: 数据库查出来的该题字典 {question_id, text, type, options...}
        :param survey_id: 所属问卷ID
        :param refresh_callback: 当发生删除/复制等大动作时，回调主窗口刷新列表
        """
        super().__init__(master, bg="white", bd=1, relief="solid")
        self.pack(fill=tk.X, padx=10, pady=10)  # 每个题目之间留空隙

        self.q_data = question_data
        self.survey_id = survey_id
        self.refresh_callback = refresh_callback
        self.checker = ViolationChecker()
        self.q_id = question_data['question_id']
        self.q_type = question_data['type']

        # 内部状态
        self.options_widgets = []  # 存储选项的 Entry 组件

        self.create_ui()

    def create_ui(self):
        # --- 第一行：标题编辑区 ---
        # 1) 显示 "1. 标题" (点击可编辑)
        header_frame = tk.Frame(self, bg="white")
        header_frame.pack(fill=tk.X, padx=10, pady=10)

        # 必填提示 (红色星号)
        tk.Label(header_frame, text="*", fg="red", bg="white", font=("Arial", 12)).pack(side=tk.LEFT)

        # 题号
        idx_text = f"{self.q_data['index']}."
        tk.Label(header_frame, text=idx_text, bg="white", font=("Arial", 12, "bold")).pack(side=tk.LEFT)

        # 题目文本输入框 (对应图片中的标题输入)
        self.title_entry = tk.Entry(header_frame, font=("Arial", 12), bd=0, bg="#F9F9F9")
        self.title_entry.insert(0, self.q_data['text'])
        self.title_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        # 焦点离开时自动保存标题
        self.title_entry.bind("<FocusOut>", self.save_title)

        # --- 第二行：选项区域 (仅针对单选/多选) ---
        self.options_container = tk.Frame(self, bg="white")
        self.options_container.pack(fill=tk.X, padx=20)

        if self.q_type in ["choice", "radio", "checkbox"]:
            self.load_options()

            # 添加选项按钮
            add_opt_btn = tk.Button(self, text="⊞ 选项 (添加)", command=self.add_new_option,
                                    bg="white", fg="#2196F3", bd=0, cursor="hand2")
            add_opt_btn.pack(anchor="w", padx=20, pady=5)

        elif self.q_type == "text":
            tk.Label(self.options_container, text="[ 用户在此处输入文本 ]", fg="gray", bg="white").pack(anchor="w",
                                                                                                        pady=10)

        # --- 第三行：底部工具栏 (完成编辑、复制、删除) ---
        # 分割线
        tk.Frame(self, height=1, bg="#E0E0E0").pack(fill=tk.X, pady=5)

        tool_frame = tk.Frame(self, bg="white", height=40)
        tool_frame.pack(fill=tk.X, padx=10, pady=5)

        # 左侧：设置占位
        tk.Label(tool_frame, text="⚙ 题目设置", fg="gray", bg="white").pack(side=tk.LEFT)

        # 右侧按钮组
        # 1. 完成编辑
        tk.Button(tool_frame, text="完成编辑", bg="#2196F3", fg="white",
                  command=self.save_all).pack(side=tk.RIGHT, padx=5)

        # 2. 更多 (...) - 占位
        tk.Label(tool_frame, text="•••", fg="gray", bg="white", font=("Arial", 14)).pack(side=tk.RIGHT, padx=5)

        # 3. 删除 (垃圾桶 🗑️)
        tk.Button(tool_frame, text="🗑️", command=self.delete_me,
                  bg="white", bd=0, cursor="hand2").pack(side=tk.RIGHT, padx=5)

        # 4. 复制 (加号 ❐)
        tk.Button(tool_frame, text="❐", command=self.copy_me,
                  bg="white", bd=0, cursor="hand2").pack(side=tk.RIGHT, padx=5)

    def load_options(self):
        """加载现有选项到界面"""
        # 清空
        for widget in self.options_container.winfo_children():
            widget.destroy()


        import sqlite3
        conn = sqlite3.connect("database/survey_system.db")
        cursor = conn.cursor()
        cursor.execute("SELECT option_id, option_text FROM Option WHERE question_id = ? ORDER BY option_index",
                       (self.q_id,))
        rows = cursor.fetchall()
        conn.close()

        for opt_id, opt_text in rows:
            self.create_option_row(opt_id, opt_text)

    def create_option_row(self, opt_id, text):
        """创建单个选项行：[图标] [输入框] [删除X]"""
        row = tk.Frame(self.options_container, bg="white")
        row.pack(fill=tk.X, pady=2)

        # 图标 (单选圆圈 / 多选方块)
        icon = "○" if self.q_type in ['radio', 'choice'] else "□"
        tk.Label(row, text=icon, fg="gray", bg="white", font=("Arial", 14)).pack(side=tk.LEFT)

        # 选项文本输入
        entry = tk.Entry(row, bg="white", bd=0, font=("Arial", 11))
        entry.insert(0, text)
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        # 失去焦点保存
        entry.bind("<FocusOut>", lambda e, oid=opt_id, ent=entry: self.save_option(oid, ent.get()))

        # 删除按钮 (X)
        del_btn = tk.Button(row, text="✕", bg="white", bd=0, fg="gray", cursor="hand2",
                            command=lambda oid=opt_id: self.delete_option_ui(oid))
        del_btn.pack(side=tk.RIGHT)

    # --- 逻辑操作 ---

    def save_title(self, event=None):
        """保存题目文本"""
        new_text = self.title_entry.get().strip()
        if not new_text:
            messagebox.showwarning("提示", "题目不能为空")
            return

        is_v, word = self.checker.check_text(new_text)
        if is_v:
            messagebox.showerror("违规", f"题目包含违规词：{word}")
            # 回滚或清空，这里暂时不清空，让用户改
            return

        update_question_text(self.q_id, new_text)
        # print(f"题目 {self.q_id} 更新为 {new_text}")

    def save_option(self, option_id, new_text):
        """保存选项文本"""
        new_text = new_text.strip()
        if not new_text:
            return
        is_v, word = self.checker.check_text(new_text)
        if is_v:
            messagebox.showerror("违规", f"选项包含违规词：{word}")
            return
        update_option_text(option_id, new_text)

    def add_new_option(self):
        """添加新选项"""
        # 默认文字
        count = len(self.options_container.winfo_children()) + 1
        text = f"选项{count}"
        # 写入数据库
        new_id = add_option(self.q_id, count, text)
        # 刷新 UI
        self.create_option_row(new_id, text)

        # module_a/ui_editor.py -> QuestionWidget 类

    def delete_option_ui(self, option_id):
        """删除选项"""
        # 指定 parent=self，保证弹窗在编辑器之上
        if messagebox.askyesno("确认", "是否确认删除该选项？", parent=self):
            delete_option(option_id)
            self.load_options()  # 重新加载刷新

            # 【关键修改】强制拉回编辑器窗口
            top = self.winfo_toplevel()
            top.lift()
            top.focus_force()

        # module_a/ui_editor.py -> QuestionWidget 类

    def delete_me(self):
        """删除本题"""
        # 指定 parent=self
        if messagebox.askyesno("确认", "是否确认删除该题目？此操作不可逆。", parent=self):
            delete_question(self.q_id)
            self.refresh_callback()  # 通知主界面刷新整个列表

             # 【关键修改】强制拉回编辑器窗口
            # 注意：虽然 self (这个题目组件) 即将被销毁或刷新，
            # 但 refresh_callback 会重建界面，编辑器窗口(Toplevel)依然存在
            top = self.winfo_toplevel()
            top.lift()
            top.focus_force()

        # module_a/ui_editor.py 中的 QuestionWidget 类

    def copy_me(self):
        """复制本题"""
        import sqlite3
        conn = sqlite3.connect("database/survey_system.db")
        cursor = conn.cursor()

        # 1. 【关键修改】计算新的 Index
        # 查询当前问卷最大的 index
        cursor.execute("SELECT MAX(question_index) FROM Question WHERE survey_id = ?", (self.survey_id,))
        row = cursor.fetchone()
        max_index = row[0] if row[0] is not None else 0
        new_index = max_index + 1

        # 2. 复制题目 (使用新计算的 index)
        new_text = self.title_entry.get()
        # 注意：这里我们手动插入 Question 表，因为我们需要拿到新的 new_q_id
        cursor.execute('''
            INSERT INTO Question (survey_id, question_index, question_text, question_type)
            VALUES (?, ?, ?, ?)
        ''', (self.survey_id, new_index, new_text, self.q_type))
        new_q_id = cursor.lastrowid

        # 3. 复制选项
        cursor.execute("SELECT option_text FROM Option WHERE question_id = ? ORDER BY option_index", (self.q_id,))
        opts = cursor.fetchall()

        for idx, (txt,) in enumerate(opts, 1):
            # 插入选项
            cursor.execute('''
                INSERT INTO Option (question_id, option_index, option_text)
                VALUES (?, ?, ?)
            ''', (new_q_id, idx, txt))

        conn.commit()
        conn.close()

        # 4. 刷新界面
        self.refresh_callback()

    # module_a/ui_editor.py 中的 QuestionWidget 类

    def save_all(self):
        """完成编辑按钮"""
        # 1. 保存标题
        self.save_title()

        # 2. 弹窗提示 (指定 parent=self，防止弹窗乱跑)
        messagebox.showinfo("成功", "本题编辑已完成", parent=self)

        # 3. 【关键修改】强制将编辑器窗口拉回最顶层并获取焦点
        top_window = self.winfo_toplevel()
        top_window.lift()  # 拉到最上层
        top_window.focus_force()  # 强制获取焦点


# ============================================================================
# 3. 主窗口类：问卷编辑器 (SurveyEditorWindow)
# 管理整体流程：输入标题 -> 题目列表
# ============================================================================
class SurveyEditorWindow(tk.Toplevel):
    def __init__(self, master, user_id):
        super().__init__(master)
        self.title("编辑调查")
        self.geometry("450x800")  # 模仿手机竖屏比例，如你截图所示
        self.user_id = user_id
        self.checker = ViolationChecker()

        self.survey_id = None

        # 容器：用于切换 "标题输入页" 和 "编辑列表页"
        self.container = tk.Frame(self)
        self.container.pack(fill=tk.BOTH, expand=True)

        self.show_title_input_page()

    # ------------------------------------------------------------------------
    # 阶段 1: 标题输入页 (见你上传的图1)
    # ------------------------------------------------------------------------
    def show_title_input_page(self):
        for widget in self.container.winfo_children():
            widget.destroy()

        page = tk.Frame(self.container, bg="#F0F2F5")
        page.pack(fill=tk.BOTH, expand=True)

        tk.Label(page, text="从空白创建调查", font=("Arial", 16, "bold"), bg="#F0F2F5").pack(pady=(40, 10))

        # 标题输入框
        self.init_title_entry = tk.Text(page, height=5, width=30, font=("Arial", 12), bd=0, relief="flat")
        self.init_title_entry.pack(pady=10, padx=20)
        self.init_title_entry.insert("1.0", "请输入标题")
        # 简单的占位符效果
        self.init_title_entry.bind("<FocusIn>", lambda e: self.init_title_entry.delete("1.0", tk.END))

        # 创建按钮
        btn = tk.Button(page, text="创建调查", bg="#2196F3", fg="white", font=("Arial", 12, "bold"),
                        relief="flat", pady=10, command=self.create_survey_action)
        btn.pack(fill=tk.X, padx=20, pady=20)

    def create_survey_action(self):
        title = self.init_title_entry.get("1.0", tk.END).strip()
        if not title or title == "请输入标题":
            messagebox.showwarning("提示", "标题不能为空")
            return

        # 违规检查
        is_v, word = self.checker.check_text(title)
        if is_v:
            messagebox.showerror("违规", f"标题包含违规词：{word}")
            # 记录违规但不创建，或者创建为 closed
            # 这里逻辑：如果不合规，禁止创建
            return

        # 写入数据库
        self.survey_id = add_survey(self.user_id, title, "draft")
        # 进入编辑页
        self.show_editor_page()

    # ------------------------------------------------------------------------
    # 阶段 2: 编辑列表页 (见你上传的图2)
    # ------------------------------------------------------------------------
    def show_editor_page(self):
        for widget in self.container.winfo_children():
            widget.destroy()

            # --- 顶部固定栏 (小房子 + 完成编辑) ---
        top_bar = tk.Frame(self.container, bg="white", height=50)
        top_bar.pack(fill=tk.X, side=tk.TOP)

        # 1. 小房子按钮 (左侧)
        home_btn = tk.Button(top_bar, text="🏠", font=("Arial", 16), bd=0, bg="white", cursor="hand2",
                             command=self.destroy)
        home_btn.pack(side=tk.LEFT, padx=10, pady=5)

        tk.Label(top_bar, text="编辑调查", font=("Arial", 14), bg="white").pack(side=tk.LEFT, padx=20)

        # 2. 【新增】完成编辑按钮 (右侧)
        finish_btn = tk.Button(top_bar, text="完成编辑", bg="#4CAF50", fg="white",
                               font=("Arial", 12, "bold"), relief="flat", padx=15,
                               cursor="hand2",
                               command=self.finish_editing)  # 绑定新方法
        finish_btn.pack(side=tk.RIGHT, padx=20, pady=8)

        # --- 问卷标题区域 (可修改) ---
        title_frame = tk.Frame(self.container, bg="white", pady=20)
        title_frame.pack(fill=tk.X)

        # 获取当前标题
        detail = get_full_survey_detail(self.survey_id)
        current_title = detail['survey_title']

        # 标题输入框 (蓝色大字)
        self.main_title_entry = tk.Entry(title_frame, font=("Arial", 18, "bold"), fg="#2196F3",
                                         bg="white", bd=0, justify="center")
        self.main_title_entry.insert(0, current_title)
        self.main_title_entry.pack(fill=tk.X, padx=20)
        self.main_title_entry.bind("<FocusOut>", self.update_survey_title_action)

        tk.Label(title_frame, text="添加问卷说明", fg="gray", bg="white").pack(pady=5)

        # --- 中间题目列表 (可滚动) ---
        # 使用我们封装的 ScrollableFrame
        self.scroll_area = ScrollableFrame(self.container)
        self.scroll_area.pack(fill=tk.BOTH, expand=True)

        # --- 底部固定栏 (添加题目按钮) ---
        bottom_bar = tk.Frame(self.container, bg="white", height=60)
        bottom_bar.pack(fill=tk.X, side=tk.BOTTOM)

        # 左下角添加按钮
        add_btn = tk.Button(bottom_bar, text="⊞ 添加题目", bg="white", fg="#2196F3",
                            font=("Arial", 12), bd=1, relief="solid",
                            command=self.open_add_question_modal)
        add_btn.pack(side=tk.LEFT, padx=20, pady=10, fill=tk.X, expand=True)

        # 批量添加 (占位)
        batch_btn = tk.Button(bottom_bar, text="批量添加题目", bg="#F5F5F5", fg="black",
                              font=("Arial", 12), bd=0)
        batch_btn.pack(side=tk.RIGHT, padx=20, pady=10, fill=tk.X, expand=True)

        # 加载题目
        self.render_questions()

    def update_survey_title_action(self, event):
        new_title = self.main_title_entry.get().strip()
        if not new_title:
            messagebox.showwarning("提示", "标题不能为空")
            return

        is_v, word = self.checker.check_text(new_title)
        if is_v:
            messagebox.showerror("违规", f"标题包含违规词：{word}")
            # 这里可以考虑 add_violation 记录，但编辑器里一般直接阻断
            return

        update_survey_title(self.survey_id, new_title)

        # module_a/ui_editor.py -> SurveyEditorWindow 类

    def finish_editing(self):
        """点击完成编辑按钮触发"""
        # 1. 强制保存一下标题 (防止用户修改了标题但光标还在输入框内，未触发 FocusOut)
        # 传入 None 是因为我们的 update_survey_title_action 接受 event 参数，但并没有使用它
        self.update_survey_title_action(None)

        # 2. 给予用户反馈
        # messagebox.showinfo("保存成功", "问卷内容已保存！") # 可选，或者直接关闭更流畅

        # 3. 关闭窗口 (回到主面板)
        self.destroy()

    def render_questions(self):
        """读取数据库，渲染所有 QuestionWidget"""
        # 清空列表
        for widget in self.scroll_area.scrollable_frame.winfo_children():
            widget.destroy()

        data = get_full_survey_detail(self.survey_id)
        questions = data.get('questions', [])

        for q in questions:
            # 创建题目组件
            qw = QuestionWidget(self.scroll_area.scrollable_frame, q, self.survey_id, self.render_questions)
            # 只要创建了实例，它自己会 pack 显示出来

    # ------------------------------------------------------------------------
    # 阶段 3: 选择题目类型弹窗 (见你上传的图3)
    # ------------------------------------------------------------------------
    def open_add_question_modal(self):
        # 创建一个模态弹窗
        modal = tk.Toplevel(self)
        modal.title("添加题目")
        modal.geometry("300x400")
        modal.transient(self)
        modal.grab_set()

        tk.Label(modal, text="添加基础题型", font=("Arial", 12, "bold"), pady=10).pack()

        # 图标网格 (简化为按钮列表)
        btn_frame = tk.Frame(modal)
        btn_frame.pack(fill=tk.BOTH, expand=True, padx=20)

        types = [
            ("单选题", "choice"),
            ("多选题", "checkbox"),
            ("填空题", "text")
        ]

        for label, q_type in types:
            tk.Button(btn_frame, text=label, height=2, width=10,
                      command=lambda t=q_type: self.add_question_action(t, modal)).pack(pady=5)

    def add_question_action(self, q_type, modal_window):
        modal_window.destroy()

        # 计算新题目的 index (当前总数 + 1)
        data = get_full_survey_detail(self.survey_id)
        new_index = len(data['questions']) + 1

        # 默认标题
        default_titles = {
            "choice": "单选题标题",
            "checkbox": "多选题标题",
            "text": "填空题标题"
        }

        # 写入数据库
        q_id = add_question(self.survey_id, new_index, default_titles[q_type], q_type)

        # 如果是选择题，默认加两个选项
        if q_type in ["choice", "checkbox"]:
            add_option(q_id, 1, "选项1")
            add_option(q_id, 2, "选项2")

        # 刷新列表
        self.render_questions()