import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import sys
import os
import socket
import threading
import json
import time
from typing import Optional, Dict, List, Any

# =====================================================
# 导入 db_proxy 替代 db_utils
# =====================================================
# 假设 db_proxy.py 在当前目录或已在 sys.path 中
try:
    # 导入同级或上级目录的 db_proxy
    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(current_dir)
    sys.path.append(current_dir)
    if parent_dir not in sys.path:
        sys.path.append(parent_dir)

    import db_proxy  # <-- 导入 db_proxy

    # 引入其他模块（保持不变）
    # 假设结构是 ../module_a/ui_editor_treading.py
    sys.path.append(os.path.join(parent_dir, "module_a"))
    from ui_editor_treading import SurveyEditorWindow  # 导入 A 的编辑器

    # 假设结构是 ../module_b/fill_survey_gui_treading.py
    sys.path.append(os.path.join(parent_dir, "module_b"))
    from fill_survey_gui_treading import MainWindow as FillSurveyMainWindow

    from generate_chart_window import generate_chart_image  # 导入图表生成

except ImportError as e:
    # 移除 sys.exit(1) 以便在 IDE 中更好地调试
    print(f"导入错误: 请确保 db_proxy.py 和相关模块存在于正确路径中: {e}")
    # 在实际应用中，如果模块缺失，这里应该显示 messagebox 并退出
    # messagebox.showerror("导入错误", f"请确保 db_proxy.py 和相关模块存在于正确路径中: {e}")
    # sys.exit(1)


# =====================================================
# Dashboard View (内嵌式主面板) - 核心修改
# =====================================================
class DashboardView(tk.Frame):
    def __init__(self, master, user_id, sock=None):
        super().__init__(master)
        self.master = master
        self.user_id = user_id
        self.sock = sock  # <--- 存储 Socket 对象

        self.configure(bg="#F0F0F0")

        # 内部状态
        self.current_survey_id: Optional[int] = None
        self.current_questions_map: Dict[str, int] = {}  # "题干": id
        self.chart_image_ref: Optional[tk.PhotoImage] = None  # 防止图片回收
        self.current_list_type = "mine"  # 默认显示我创建的
        self.current_survey_title = ""  # 存储当前选中问卷的标题

        # UI 元素引用 (用于线程更新)
        self.loading_label: Optional[ttk.Label] = None
        self.loading_chart_label: Optional[ttk.Label] = None
        self.my_answer_loading_label: Optional[ttk.Label] = None

        # ============================================
        # 1. 顶部内容区域 (左右分栏布局)
        # ============================================
        self.content_frame = tk.Frame(self, bg="#FFFFFF")
        self.content_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=20, pady=20)

        # 使用 PanedWindow 将内容区分为左右两部分
        self.paned_win = tk.PanedWindow(self.content_frame, orient=tk.HORIZONTAL, sashrelief=tk.RAISED)
        self.paned_win.pack(fill=tk.BOTH, expand=True)

        # --- 左侧：问卷列表 ---
        self.left_frame = tk.Frame(self.paned_win, bg="#FAFAFA", width=300)
        self.paned_win.add(self.left_frame, minsize=300)

        # 列表切换按钮区
        self.list_controls_frame = tk.Frame(self.left_frame, bg="#FAFAFA")
        self.list_controls_frame.pack(pady=5, fill=tk.X, padx=5)

        ttk.Button(self.list_controls_frame, text="我创建的问卷",
                   command=lambda: self.switch_survey_list("mine")).pack(side=tk.LEFT, expand=True, padx=2)
        ttk.Button(self.list_controls_frame, text="我填过的问卷",
                   command=lambda: self.switch_survey_list("filled")).pack(side=tk.LEFT, expand=True, padx=2)

        # 【已修复 list_title 缺失】
        self.list_title = tk.Label(self.left_frame, text="问卷列表", font=("Arial", 12, "bold"), bg="#FAFAFA",
                                   anchor='w')
        self.list_title.pack(pady=(10, 0), fill=tk.X, padx=5)

        # 问卷列表 Treeview
        cols = ("ID", "标题", "状态", "创建者")  # 新增列以匹配 load_surveys 的逻辑
        self.tree = ttk.Treeview(self.left_frame, columns=cols, show='headings', height=15)
        self.tree.heading("ID", text="ID")
        self.tree.column("ID", width=40, stretch=tk.NO)
        self.tree.heading("标题", text="标题")
        self.tree.column("标题", stretch=tk.YES)
        self.tree.heading("状态", text="状态")
        self.tree.column("状态", width=60, stretch=tk.NO)
        self.tree.heading("创建者", text="创建者")
        self.tree.column("创建者", width=80, stretch=tk.NO)
        self.tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 绑定点击事件
        self.tree.bind("<<TreeviewSelect>>", self.on_survey_select)

        # --- 右侧：内容容器 (图表/答案) ---
        self.right_frame = tk.Frame(self.paned_win, bg="white")
        self.paned_win.add(self.right_frame)

        # 初始化右侧面板内容
        self.create_right_panel_content()

        # 初始化加载数据 (默认加载我创建的)
        # 【修改】首次加载也使用线程
        self.load_surveys(self.current_list_type)

    def create_right_panel_content(self):
        """创建右侧面板的所有子控件，并控制它们的显示/隐藏"""

        # ------------------- 1. 图表生成控件 (controls_frame) -------------------
        self.controls_frame = tk.Frame(self.right_frame, bg="white")

        tk.Label(self.controls_frame, text="选择题目:", bg="white").pack(side=tk.LEFT)
        self.question_combo = ttk.Combobox(self.controls_frame, state="readonly", width=30)
        self.question_combo.pack(side=tk.LEFT, padx=5)

        tk.Label(self.controls_frame, text="图表类型:", bg="white").pack(side=tk.LEFT, padx=10)
        self.chart_type_combo = ttk.Combobox(self.controls_frame, state="readonly", width=15,
                                             values=["pie", "bar", "bar_h", "line_answer", "text_answer"])
        self.chart_type_combo.current(0)
        self.chart_type_combo.pack(side=tk.LEFT, padx=5)

        tk.Button(self.controls_frame, text="生成图表", command=self.generate_chart, bg="#2196F3", fg="white").pack(
            side=tk.LEFT, padx=15)

        # ------------------- 2. 图表/答案内容显示区 (chart_container) -------------------
        # 统一使用这个容器来显示图表或答案 Treeview
        self.content_display_container = tk.Frame(self.right_frame, bg="white")
        self.content_display_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        # 图表标签 (初始显示文本)
        self.chart_label = tk.Label(self.content_display_container, text="请选择左侧问卷。", bg="#EEEEEE")
        self.chart_label.pack(expand=True, fill=tk.BOTH)

        # ------------------- 3. 答案 Treeview (初始隐藏) -------------------
        self.answer_tree_frame = tk.Frame(self.content_display_container, bg="white")
        # 不需要 pack，只在需要时显示

        self.tree_ans = ttk.Treeview(self.answer_tree_frame, columns=("Question", "Answer"), show='headings')
        self.tree_ans.heading("Question", text="题目")
        self.tree_ans.column("Question", width=250, stretch=tk.YES)
        self.tree_ans.heading("Answer", text="我的答案")
        self.tree_ans.column("Answer", width=250, stretch=tk.YES)

        # 滚动条
        vsb = ttk.Scrollbar(self.answer_tree_frame, orient="vertical", command=self.tree_ans.yview)
        self.tree_ans.configure(yscrollcommand=vsb.set)

        vsb.pack(side='right', fill='y')
        self.tree_ans.pack(side='left', fill='both', expand=True)

        # ============================================
        # 2. 底部固定边栏
        # ============================================
        self.bottom_bar = tk.Frame(self, height=80, bg="#333333")
        self.bottom_bar.pack(side=tk.BOTTOM, fill=tk.X)
        self.bottom_bar.pack_propagate(False)

        self.fill_btn = tk.Button(
            self.bottom_bar, text="✍ 填写问卷", font=("Arial", 14, "bold"),
            bg="#2196F3", fg="white", cursor="hand2",
            command=self.open_fill_survey
        )
        self.create_btn = tk.Button(
            self.bottom_bar, text="＋ 创建问卷", font=("Arial", 14, "bold"),
            bg="#4CAF50", fg="white", cursor="hand2",
            command=self.open_editor
        )
        self.fill_btn.place(relx=0.35, rely=0.5, anchor="center", width=150, height=50)
        self.create_btn.place(relx=0.65, rely=0.5, anchor="center", width=150, height=50)

    def get_list_display_name(self, list_type: str) -> str:
        """根据列表类型返回显示名称"""
        if list_type == "mine":
            return "我创建的问卷"
        elif list_type == "filled":
            return "我填过的问卷"
        else:
            return "问卷列表"

    def switch_survey_list(self, list_type: str):
        """切换显示 'mine' 或 'filled' 问卷列表"""
        self.current_list_type = list_type
        # 【修改】调用线程加载
        self.load_surveys(list_type)

        # 初始状态：隐藏所有内容，仅显示默认提示
        self.controls_frame.pack_forget()
        self.answer_tree_frame.pack_forget()
        if hasattr(self, 'answers_title_label'):
            self.answers_title_label.pack_forget()

        self.chart_label.config(
            text=f"已切换到[{self.get_list_display_name(list_type)}]问卷列表。请选择问卷。", image="")
        self.chart_label.pack(expand=True, fill=tk.BOTH)
        self.chart_image_ref = None

    def load_surveys(self, list_type: str):
        """
        【修改】启动线程来加载问卷列表，避免卡顿
        """
        self.current_list_type = list_type

        # 清空 Treeview
        for item in self.tree.get_children():
            self.tree.delete(item)

        # 移除旧的加载提示
        if self.loading_label:
            self.loading_label.destroy()

        # 1. 显示加载中的提示
        self.loading_label = tk.Label(self.left_frame, text="正在加载问卷列表，请稍候...", font=('Arial', 12),
                                      bg="#FAFAFA")
        self.loading_label.pack(pady=10)

        # 2. 启动线程执行 I/O 操作
        threading.Thread(target=self._load_surveys_thread, args=(list_type,)).start()

    def _load_surveys_thread(self, list_type: str):
        """
        [新增] 在后台线程中执行 I/O 阻塞操作（网络请求）
        """
        surveys: List[Dict[str, Any]] = []
        error_msg: Optional[str] = None
        try:
            if list_type == "filled":
                # 原始的多次网络请求逻辑
                filled_survey_ids = db_proxy.get_surveys_filled_by_user(self.sock, self.user_id)
                if filled_survey_ids is None: filled_survey_ids = []

                for survey_id in filled_survey_ids:
                    # ⚠️ 每次循环都是一个网络请求
                    survey_detail = db_proxy.get_survey(self.sock, survey_id)

                    if survey_detail and survey_detail.get('survey_status') == 'active':
                        surveys.append(survey_detail)

            elif list_type == "mine":
                surveys = db_proxy.get_public_surveys_by_user_id(self.sock, self.user_id)
                if surveys is None: surveys = []

        except Exception as e:
            error_msg = f"加载问卷列表失败: {e}"

        # 3. 线程完成后，使用 after 安全地回到主线程更新 UI
        self.master.after(0, self._update_surveys_ui, surveys, error_msg, list_type)

    def _update_surveys_ui(self, surveys: List[Dict[str, Any]], error_msg: Optional[str], list_type: str):
        """
        [新增] 在主线程中更新 UI
        """
        # 移除加载提示
        if self.loading_label:
            self.loading_label.destroy()

        # 处理错误
        if error_msg:
            messagebox.showerror("网络错误", error_msg)
            surveys = []  # 清空列表

        # 清空 Treeview (再次确保)
        for item in self.tree.get_children():
            self.tree.delete(item)

        # 插入数据
        for s in surveys:
            survey_id = s.get('survey_id')
            title = s.get('survey_title', '未知标题')
            status = s.get('survey_status', '未知状态')
            created_by_id = s.get('created_by')

            # 插入数据
            self.tree.insert('', 'end',
                             values=(survey_id, title, status, f"ID:{created_by_id}"),
                             tags=(survey_id,))

        # 更新状态栏或标题
        self.list_title.config(text=f"当前列表：{self.get_list_display_name(list_type)} ({len(surveys)} 份)")

    def on_survey_select(self, event):
        """当选中问卷时，加载该问卷的题目并根据列表类型调整右侧控制"""
        selected = self.tree.selection()
        if not selected:
            return

        item = self.tree.item(selected[0])
        # 修正：values 列表顺序为 ("ID", "标题", "状态", "创建者")
        survey_id = item['values'][0]
        title = item['values'][1]

        self.current_survey_id = survey_id
        self.current_survey_title = title

        # 隐藏所有内容容器
        self.controls_frame.pack_forget()
        self.chart_label.pack_forget()
        self.answer_tree_frame.pack_forget()

        if hasattr(self, 'answers_title_label'):
            self.answers_title_label.pack_forget()

        if self.current_list_type == "mine":
            # Created Survey: 显示图表生成控件
            self.controls_frame.pack(fill=tk.X, padx=10, pady=(10, 0))
            self.chart_label.pack(expand=True, fill=tk.BOTH)  # 重新显示 chart_label 用于承载图表

            # 【修改】启动线程获取问卷详情
            self.chart_label.config(text="正在加载问卷详情...", image="")
            threading.Thread(target=self._load_survey_detail_thread, args=(survey_id, title)).start()


        elif self.current_list_type == "filled":
            # Filled Survey: 直接在右侧面板显示答案
            # 【修改】启动线程显示答案
            self.display_my_answers_in_right_panel(survey_id, title)

    def _load_survey_detail_thread(self, survey_id: int, title: str):
        """[新增] 后台线程获取问卷详情和题目列表"""
        detail: Optional[Dict[str, Any]] = None
        error_msg: Optional[str] = None
        try:
            detail = db_proxy.get_full_survey_detail(self.sock, survey_id)
        except Exception as e:
            error_msg = f"获取问卷详情失败: {e}"

        self.master.after(0, self._update_survey_detail_ui, detail, error_msg, title)

    def _update_survey_detail_ui(self, detail: Optional[Dict[str, Any]], error_msg: Optional[str], title: str):
        """[新增] 主线程更新问卷详情UI (更新题目下拉列表)"""

        if error_msg:
            messagebox.showerror("错误", error_msg)
            self.chart_label.config(text="获取问卷详情失败或网络错误", image="")
            return

        if not detail:
            self.chart_label.config(text="问卷详情为空或网络错误", image="")
            return

        combo_values: List[str] = []
        self.current_questions_map = {}  # 清空旧的映射
        for q in detail.get('questions', []):
            label = f"{q.get('index', 'N/A')}. {q.get('text', 'N/A')} [{q.get('type', 'N/A')}]"
            self.current_questions_map[label] = q.get('question_id')
            combo_values.append(label)

        self.question_combo['values'] = combo_values
        if combo_values:
            self.question_combo.current(0)

        self.chart_label.config(text=f"已选择: {title}，请选择题目并生成图表", image="")
        self.chart_image_ref = None

    def display_my_answers_in_right_panel(self, survey_id, title):
        """
        【修改】在右侧面板中直接显示用户对当前问卷的完整答案
        """

        # 确保答案 Treeview 区域显示
        self.answer_tree_frame.pack(fill=tk.BOTH, expand=True)

        # 清空 Treeview
        for item in self.tree_ans.get_children():
            self.tree_ans.delete(item)

        # 更新右侧标题
        if not hasattr(self, 'answers_title_label'):
            self.answers_title_label = tk.Label(self.right_frame, text="", font=("Arial", 14, "bold"),
                                                bg="white")
        self.answers_title_label.config(text=f"我的答案 - {title}")
        self.answers_title_label.pack(pady=(10, 5), padx=10, fill=tk.X)

        # 1. 显示加载中的提示
        if self.my_answer_loading_label:
            self.my_answer_loading_label.destroy()

        self.my_answer_loading_label = tk.Label(self.answer_tree_frame, text="正在加载答案，请稍候...",
                                                font=('Arial', 12), bg="white")
        self.my_answer_loading_label.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

        # 2. 启动线程
        threading.Thread(target=self._load_my_answers_thread, args=(survey_id,)).start()

    def _load_my_answers_thread(self, survey_id: int):
        """
        [新增] 在后台线程中加载用户答案
        """
        answers: List[Dict[str, Any]] = []
        error_msg: Optional[str] = None
        try:
            # 【I/O 阻塞操作】
            answers = db_proxy.get_user_survey_answers_detail(self.sock, survey_id, self.user_id)
            if answers is None: answers = []

        except Exception as e:
            error_msg = f"加载答案失败: {e}"

        # 3. 线程完成后，使用 after 安全地回到主线程更新 UI
        self.master.after(0, self._update_my_answers_ui, answers, error_msg)

    def _update_my_answers_ui(self, answers: List[Dict[str, Any]], error_msg: Optional[str]):
        """
        [新增] 在主线程中更新答案展示 UI
        """
        # 移除加载提示
        if self.my_answer_loading_label:
            self.my_answer_loading_label.destroy()

        if error_msg:
            # 如果加载答案失败，则显示错误信息
            self.answer_tree_frame.pack_forget()
            self.controls_frame.pack_forget()
            self.chart_label.config(text=f"加载答案失败: {error_msg}", fg="red", bg="white")
            self.chart_label.pack(expand=True, fill=tk.BOTH)
            return

        # 插入数据
        for ans in answers:
            q_text = ans.get('question_text', 'N/A')
            answer_text = str(ans.get('answer', '未作答'))

            # 简单处理长文本显示
            if len(answer_text) > 80:
                answer_text = answer_text[:77] + "..."

            self.tree_ans.insert("", "end", values=(q_text, answer_text))

    def generate_chart(self):
        """
        【已修改】增加题目类型预判，限制图表/文本报告生成逻辑
        """
        if self.current_list_type == "filled":
            messagebox.showwarning("提示", "您正在查看已填问卷列表，不支持生成图表。")
            return

        if not self.current_survey_id:
            messagebox.showwarning("提示", "请先选择一个问卷")
            return

        q_label = self.question_combo.get()
        if not q_label:
            messagebox.showwarning("提示", "请选择题目")
            return

        q_id = self.current_questions_map.get(q_label)
        c_type = self.chart_type_combo.get()
        title = self.current_survey_title
        q_text = q_label

        # --- 核心逻辑判断：根据题干中的类型标识限制生成内容 ---
        # 题干格式通常为 "1. 题目文本 [type]"
        is_text_type = "[text]" in q_label.lower() or "[textarea]" in q_label.lower()

        if is_text_type:
            if c_type != "text_answer":
                messagebox.showwarning("提示", "文本类题目仅支持生成 'text_answer' 文字报告。")
                return
        else:
            if c_type == "text_answer":
                messagebox.showwarning("提示", "选择类题目请选择饼图、柱状图或趋势图。")
                return

        # 在显示图表前，确保隐藏答案面板
        self.answer_tree_frame.pack_forget()
        self.chart_label.pack(expand=True, fill=tk.BOTH)
        if hasattr(self, 'answers_title_label'):
            self.answers_title_label.pack_forget()

        # 显示加载状态
        if self.loading_chart_label:
            self.loading_chart_label.destroy()

        load_msg = "正在生成文字报告..." if is_text_type else "正在生成图表..."
        self.loading_chart_label = tk.Label(self.chart_label, text=load_msg,
                                            font=('Arial', 14), bg="#EEEEEE")
        self.loading_chart_label.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

        # 启动线程进行处理
        threading.Thread(target=self._generate_chart_thread, args=(q_id, c_type, title, q_text)).start()
    def _generate_chart_thread(self, q_id: int, c_type: str, title: str, q_text: str):
        """
        [修改] result 现在可能是 PhotoImage 或 String (报告文本)
        """
        result: Any = None
        error_msg: Optional[str] = None
        try:
            # 这里的 generate_chart_image 内部会根据 c_type 调用不同的后端逻辑
            result = generate_chart_image(self.current_survey_id, q_id, c_type, sock=self.sock)
        except Exception as e:
            error_msg = f"生成失败: {e}"

        # 传递 c_type 以便 UI 线程判断如何渲染
        self.master.after(0, self._display_chart_ui_flexible, result, error_msg, title, q_text, c_type)

    def _display_chart_ui_flexible(self, result: Any, error_msg: Optional[str], title: str, q_text: str, c_type: str):
        """
        修正后的渲染函数：
        1. 彻底清除之前的 image 引用
        2. 根据 c_type 决定是更新 Label 的 text 还是 image
        """
        if self.loading_chart_label:
            self.loading_chart_label.destroy()

        if error_msg:
            self.chart_label.config(image="", text=f"无法处理: {error_msg}", fg="red")
            self.chart_image_ref = None
            return

        # 重要：每次更新前先重置 Label 状态，防止旧图片干扰
        self.chart_label.config(image="", text="")

        if c_type == "text_answer":
            # --- 情况 A: 处理文字报告 ---
            # 此时 result 是后端传来的 bytes 或 str
            try:
                report_content = result.decode('utf-8') if isinstance(result, bytes) else str(result)
            except Exception:
                report_content = str(result)

            full_report = f"问卷: {title}\n题目: {q_text}\n\n{report_content}"

            self.chart_label.config(
                text=full_report,
                fg="black",
                font=("Consolas", 11),  # 等宽字体适合打印报告
                justify=tk.LEFT,
                anchor="nw",  # 文本从左上角开始排版
                padx=20,
                pady=20,
                compound="none"  # 确保不尝试显示图片
            )
            self.chart_image_ref = None  # 清空图片引用

        else:
            # --- 情况 B: 处理图像图表 ---
            # 此时 result 必须是已经转换好的 PhotoImage 对象
            # 如果 generate_chart_image 返回的是 bytes，这里需要先转 PhotoImage

            self.chart_image_ref = result  # 保持引用防止 GC
            self.chart_label.config(
                image=result,
                text=f"问卷: {title}\n题目: {q_text}",
                compound="top",  # 图片在上，标题在下
                fg="black",
                font=("Arial", 10),
                justify=tk.CENTER,
                anchor="center"  # 图片居中显示
            )
    def open_fill_survey(self):
        """点击填写问卷 → 打开填写问卷主界面"""
        # 确保 FillSurveyMainWindow 接收并存储 self.sock
        if FillSurveyMainWindow:
            FillSurveyMainWindow(self.master, self.user_id, self.sock)
        else:
            messagebox.showerror("模块缺失", "填写问卷模块未导入。")

    def open_editor(self):
        """点击按钮，跳转到 A 的问卷创建界面"""
        # 确保 SurveyEditorWindow 接收并存储 self.sock
        if SurveyEditorWindow:
            SurveyEditorWindow(self.master, self.user_id, self.sock)
        else:
            messagebox.showerror("模块缺失", "问卷编辑器模块未导入。")


# =====================================================
# Main Application - 【核心修正：添加 Socket 连接和逻辑】
# =====================================================
class UserSystemApp:
    SERVER_HOST = "127.0.0.1"
    SERVER_PORT = 5000

    # 建议将 Socket 超时增加到 20 秒，以应对图表生成时的多次 I/O 阻塞
    SOCKET_TIMEOUT = 20.0

    def __init__(self, master):
        self.master = master
        self.master.title("问卷系统 - 综合管理")
        self.master.geometry("1000x700")

        self.current_user_id = None
        self.is_admin = False
        self.sock: Optional[socket.socket] = None

        # 尝试连接服务器
        if not self._connect_server():
            # 连接失败则直接退出
            self.master.quit()
            return

        # 登录容器
        self.login_frame = tk.Frame(master)
        self.login_frame.pack(expand=True, fill="both")

        self.create_login_view()

        # 启动后台监听线程
        self._start_listen_thread()

    def _connect_server(self):
        """连接服务器"""
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            # 增加超时时间以应对复杂的图表生成 I/O
            self.sock.settimeout(self.SOCKET_TIMEOUT)
            self.sock.connect((self.SERVER_HOST, self.SERVER_PORT))
            return True
        except Exception as e:
            messagebox.showerror("网络错误",
                                 f"无法连接服务器 {self.SERVER_HOST}:{self.SERVER_PORT}. 请确保服务器已运行。错误: {e}")
            return False

    def _start_listen_thread(self):
        """后台线程监听服务器消息（如强制退出）"""

        def listen_server_messages():
            # 监听线程使用较短的超时，以便于轮询和响应退出信号
            temp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            if self.sock:
                temp_sock = self.sock

            try:
                temp_sock.settimeout(0.5)  # 设置非阻塞 / 超时
                while True:
                    try:
                        data = temp_sock.recv(4096)
                        if data:
                            msg = json.loads(data.decode("utf-8"))
                            if msg.get("action") == "force_logout":
                                self.master.after(0, lambda: self._handle_force_logout(msg))  # 切换到主线程处理 UI
                                break
                    except socket.timeout:
                        pass  # 轮询继续
                    except ConnectionResetError:
                        self.master.after(0, lambda: self._handle_connection_reset())
                        break
                    except Exception as e:
                        # 其他连接错误
                        break
                    time.sleep(0.1)
            finally:
                # 注意：这里不能关闭 self.sock，因为它可能被主线程使用
                # 只有当程序退出或确认连接完全不可用时才关闭
                pass

        threading.Thread(target=listen_server_messages, daemon=True).start()

    def _handle_force_logout(self, msg):
        """处理强制退出消息"""
        reason = msg.get("reason", "账号在另一地点登录。")
        messagebox.showinfo("提示", f"你已被强制退出。原因: {reason}")
        self.master.destroy()

    def _handle_connection_reset(self):
        """处理连接被重置（服务器关闭）"""
        messagebox.showerror("连接断开", "与服务器的连接已断开，应用将关闭。")
        self.master.destroy()

    def create_login_view(self):
        # ... (登录/注册界面创建代码保持不变) ...

        tab_control = ttk.Notebook(self.login_frame)

        tab_login = ttk.Frame(tab_control)
        tab_register = ttk.Frame(tab_control)

        tab_control.add(tab_login, text='登录')
        tab_control.add(tab_register, text='注册')
        tab_control.pack(expand=1, fill='both', padx=50, pady=50)

        # --- 登录界面 ---
        ttk.Label(tab_login, text="用户名:").pack(pady=10)
        self.entry_login_name = ttk.Entry(tab_login)
        self.entry_login_name.pack(pady=5)

        ttk.Label(tab_login, text="密码:").pack(pady=10)
        self.entry_login_pwd = ttk.Entry(tab_login, show="*")
        self.entry_login_pwd.pack(pady=5)

        ttk.Button(tab_login, text="登录", command=self.login_action).pack(pady=20)

        # --- 注册界面 ---
        ttk.Label(tab_register, text="用户名:").pack(pady=5)
        self.entry_reg_name = ttk.Entry(tab_register)
        self.entry_reg_name.pack(pady=5)

        ttk.Label(tab_register, text="密码:").pack(pady=5)
        self.entry_reg_pwd = ttk.Entry(tab_register, show="*")
        self.entry_reg_pwd.pack(pady=5)

        ttk.Button(tab_register, text="注册", command=self.register_action).pack(pady=20)

    def login_action(self):
        name = self.entry_login_name.get()
        pwd = self.entry_login_pwd.get()

        if not name or not pwd:
            messagebox.showwarning("提示", "请填写完整信息")
            return

        try:
            # 1. 获取用户信息
            user = db_proxy.get_user_by_login(self.sock, name)

            if user:
                # 假设服务器端处理了哈希，这里只需要比较
                db_pwd = user.get('password')  # 假设返回的是哈希后的密码

                if db_pwd == pwd:
                    # 检查用户状态（避免禁用用户登录）
                    if user.get('user_status') == 'banned':
                        messagebox.showerror("登录失败", "您的账户已被禁用，请联系管理员。")
                        return

                    self.current_user_id = user['user_id']
                    self.is_admin = (user.get('user_status') == 'admin')
                    messagebox.showinfo("登录成功", f"欢迎 {user['user_name']}")

                    # 登录成功后，发送登录消息给服务器，关联 Socket 和 User ID
                    login_msg = {"action": "login", "params": {"user_id": self.current_user_id}}
                    self.sock.sendall(json.dumps(login_msg).encode("utf-8"))

                    self.show_dashboard()
                else:
                    messagebox.showerror("登录失败", "用户名或密码错误")
            else:
                # user 为 None 或非字典（表示用户不存在）
                messagebox.showerror("登录失败", "用户名或密码错误")
        except Exception as e:
            # 处理网络连接或解析错误
            messagebox.showerror("系统错误", f"登录或网络连接失败: {e}")

    def register_action(self):
        name = self.entry_reg_name.get()
        pwd = self.entry_reg_pwd.get()

        if not name or not pwd:
            messagebox.showwarning("提示", "请填写完整信息")
            return

        try:
            db_proxy.add_user(self.sock, user_name=name, password=pwd, user_status='active', unban_time=None)
            messagebox.showinfo("注册成功", "注册成功，请登录")
        except Exception as e:
            messagebox.showerror("注册失败", f"可能用户名已存在或网络错误: {e}")

    def show_dashboard(self):
        """登录成功后切换到 Dashboard"""
        self.login_frame.destroy()

        # 传递 self.sock 给 DashboardView
        dashboard = DashboardView(self.master, self.current_user_id, sock=self.sock)
        dashboard.pack(fill="both", expand=True)

        if self.is_admin:
            self.master.title(f"问卷系统 - 管理员模式 ({self.current_user_id})")


if __name__ == "__main__":
    root = tk.Tk()
    app = UserSystemApp(root)
    root.mainloop()