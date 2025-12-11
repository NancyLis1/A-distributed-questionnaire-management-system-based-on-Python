import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import sys
import os

# =====================================================
# 路径配置：添加上级目录以导入 db_utils
# =====================================================
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

# 确保能导入同级目录模块
if current_dir not in sys.path:
    sys.path.append(current_dir)

import db_utils  # 导入上级目录的 db_utils
from generate_chart_window import generate_chart_image

# 尝试导入 Module A 和 Module B，如果不存在则使用占位符
try:
    # 假设结构是 ../module_a/ui_editor_treading.py
    sys.path.append(os.path.join(parent_dir, "module_a"))
    from ui_editor_treading import SurveyEditorWindow
except ImportError:
    SurveyEditorWindow = None
    print("Warning: Module A not found.")

try:
    # 假设结构是 ../module_b/fill_survey_gui_treading.py
    sys.path.append(os.path.join(parent_dir, "module_b"))
    from fill_survey_gui_treading import MainWindow as FillSurveyMainWindow
except ImportError:
    FillSurveyMainWindow = None
    print("Warning: Module B not found.")


# =====================================================
# Dashboard View (内嵌式主面板) - 【已添加问卷切换和答案查看逻辑】
# =====================================================
class DashboardView(tk.Frame):
    def __init__(self, master, user_id, sock=None):
        super().__init__(master)
        self.master = master
        self.user_id = user_id
        self.sock = sock

        self.configure(bg="#F0F0F0")

        # 内部状态
        self.current_survey_id = None
        self.current_questions_map = {}  # "题干": id
        self.chart_image_ref = None  # 防止图片回收
        self.current_list_type = "mine"  # 默认显示我创建的
        self.current_survey_title = ""  # 存储当前选中问卷的标题

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
        cols = ("ID", "标题", "时间")
        self.tree = ttk.Treeview(self.left_frame, columns=cols, show='headings', height=15)
        self.tree.heading("ID", text="ID")
        self.tree.column("ID", width=40, stretch=tk.NO)
        self.tree.heading("标题", text="标题")
        self.tree.column("标题", stretch=tk.YES)
        self.tree.heading("时间", text="时间")
        self.tree.column("时间", width=100, stretch=tk.NO)
        self.tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 绑定点击事件
        self.tree.bind("<<TreeviewSelect>>", self.on_survey_select)

        # --- 右侧：内容容器 (图表/答案) ---
        self.right_frame = tk.Frame(self.paned_win, bg="white")
        self.paned_win.add(self.right_frame)

        # 初始化右侧面板内容
        self.create_right_panel_content()

        # 初始化加载数据 (默认加载我创建的)
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
                                             values=["pie", "bar", "bar_h", "line_answer", "wordcloud"])
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
        # 2. 底部固定边栏 (保持不变)
        # ... (省略 bottom_bar 的创建代码)
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

    # ... (get_list_display_name 和 switch_survey_list 方法保持不变)

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
        self.load_surveys(list_type)
        self.chart_label.config(
            text=f"已切换到[{self.get_list_display_name(list_type)}]问卷列表。请选择问卷。", image="")
        self.chart_image_ref = None
        # 初始状态：隐藏所有内容，仅显示默认提示
        self.controls_frame.pack_forget()
        self.chart_label.pack(expand=True, fill=tk.BOTH)
        self.answer_tree_frame.pack_forget()

    def load_surveys(self, list_type: str):
        # ... (load_surveys 保持不变，因为这部分逻辑是正确的)
        # 记录当前加载类型
        self.current_list_type = list_type

        surveys = []
        if list_type == "filled":
            # 1. 获取已填写问卷的 ID 列表
            try:
                filled_survey_ids = db_utils.get_surveys_filled_by_user(self.user_id)
            except Exception as e:
                messagebox.showerror("数据库错误", f"获取已填问卷ID失败: {e}")
                filled_survey_ids = []

            # 2. 遍历 ID，获取完整的问卷信息字典 (使用 db_utils.get_survey)
            for survey_id in filled_survey_ids:
                try:
                    survey_detail = db_utils.get_survey(survey_id)
                    # 仅显示已发布的（active）问卷，防止用户填写已关闭的问卷
                    if survey_detail and survey_detail.get('survey_status') == 'active':
                        surveys.append(survey_detail)
                except Exception as e:
                    # 忽略单个问卷的错误
                    print(f"Error fetching survey detail {survey_id}: {e}")

        elif list_type == "mine":
            # 获取用户自己创建的问卷
            surveys = db_utils.get_public_surveys_by_user_id(self.user_id)

        # 清空 Treeview
        for item in self.tree.get_children():
            self.tree.delete(item)

        # 核心：现在 surveys 确保是字典列表，可以安全地调用 .get()
        for s in surveys:
            survey_id = s.get('survey_id')  # 现在 s 是字典，不再是 int
            title = s.get('survey_title', '未知标题')
            status = s.get('survey_status', '未知状态')
            created_by_id = s.get('created_by')
            release_time = s.get('release_time', 'N/A')

            # 临时显示创建者 ID
            creator_name = f"ID: {created_by_id}"

            # 插入数据
            self.tree.insert('', 'end',
                             values=(survey_id, title, creator_name, status, release_time),
                             tags=(survey_id,))  # 使用 survey_id 作为 tag

        # 更新状态栏或标题
        self.list_title.config(text=f"当前列表：{self.get_list_display_name(list_type)} ({len(surveys)} 份)")

    def on_survey_select(self, event):
        """当选中问卷时，加载该问卷的题目并根据列表类型调整右侧控制"""
        selected = self.tree.selection()
        if not selected:
            return

        item = self.tree.item(selected[0])
        survey_id = item['values'][0]
        title = item['values'][1]

        self.current_survey_id = survey_id
        self.current_survey_title = title

        # 隐藏所有内容容器
        self.controls_frame.pack_forget()
        self.chart_label.pack_forget()
        self.answer_tree_frame.pack_forget()

        if self.current_list_type == "mine":
            # Created Survey: 显示图表生成控件
            self.controls_frame.pack(fill=tk.X, padx=10, pady=(10, 0))
            self.chart_label.pack(expand=True, fill=tk.BOTH)  # 重新显示 chart_label 用于承载图表

            try:
                detail = db_utils.get_full_survey_detail(survey_id)
            except Exception as e:
                messagebox.showerror("错误", f"获取问卷详情失败: {e}")
                return

            if not detail:
                return

            combo_values = []
            for q in detail['questions']:
                label = f"{q['index']}. {q['text']} [{q['type']}]"
                self.current_questions_map[label] = q['question_id']
                combo_values.append(label)

            self.question_combo['values'] = combo_values
            if combo_values:
                self.question_combo.current(0)
            self.chart_label.config(text="请选择题目并生成图表", image="")
            self.chart_image_ref = None

        elif self.current_list_type == "filled":
            # Filled Survey: 【核心修正】直接在右侧面板显示答案
            self.display_my_answers_in_right_panel(survey_id, title)

    def display_my_answers_in_right_panel(self, survey_id, title):
        """在右侧面板中直接显示用户对当前问卷的完整答案"""

        # 确保答案 Treeview 区域显示
        self.answer_tree_frame.pack(fill=tk.BOTH, expand=True)

        # 清空 Treeview
        for item in self.tree_ans.get_children():
            self.tree_ans.delete(item)

        # 更新右侧标题
        self.right_frame.pack_propagate(False)

        if hasattr(self, 'answers_title_label'):
            self.answers_title_label.destroy()

        self.answers_title_label = tk.Label(self.right_frame, text=f"我的答案 - {title}", font=("Arial", 14, "bold"),
                                            bg="white")
        self.answers_title_label.pack(pady=(10, 5), padx=10, fill=tk.X)
        self.answers_title_label.tkraise()

        try:
            # 【关键修正】：调用新增的函数，并传入 survey_id 和 user_id
            if hasattr(db_utils, 'get_user_survey_answers_detail'):
                answers = db_utils.get_user_survey_answers_detail(survey_id, self.user_id)
            else:
                answers = [
                    {"question_text": "错误: db_utils 缺少 get_user_survey_answers_detail 方法",
                     "answer": "无法获取答案详情"}]

            for ans in answers:
                q_text = ans.get('question_text', 'N/A')
                answer_text = str(ans.get('answer', '未作答'))

                # 简单处理长文本显示
                if len(answer_text) > 80:
                    answer_text = answer_text[:77] + "..."

                self.tree_ans.insert("", "end", values=(q_text, answer_text))

        except Exception as e:
            # 如果加载答案失败，则显示错误信息，并隐藏 Treeview
            self.answer_tree_frame.pack_forget()
            self.controls_frame.pack_forget()

            self.chart_label.config(text=f"加载答案失败: {e}", fg="red", bg="white")
            self.chart_label.pack(expand=True, fill=tk.BOTH)

    def generate_chart(self):
        # ... (generate_chart 保持不变)
        """生成并显示图表"""
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

        try:
            # 在显示图表前，确保隐藏答案面板
            self.answer_tree_frame.pack_forget()
            self.chart_label.pack(expand=True, fill=tk.BOTH)  # 重新显示 chart_label
            if hasattr(self, 'answers_title_label'):
                self.answers_title_label.pack_forget()

            photo = generate_chart_image(self.current_survey_id, q_id, c_type)

            self.chart_label.config(image=photo, text="")
            self.chart_image_ref = photo

        except ValueError as ve:
            self.chart_label.config(image="", text=f"无法生成图表: {str(ve)}")
        except Exception as e:
            messagebox.showerror("错误", f"生成失败: {e}")

    # ... (open_fill_survey 和 open_editor 保持不变)
    def open_fill_survey(self):
        # ...
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("提示", "请选择一个问卷进行填写")
            return

        # 提取选中问卷的ID
        item = self.tree.item(selected[0])
        survey_id = item['values'][0]

        if FillSurveyMainWindow:
            # 传递 survey_id
            FillSurveyMainWindow(self.master, self.user_id, self.sock, survey_id=survey_id)
        else:
            messagebox.showerror("错误", "填写问卷模块(Module B)未加载")

    def open_editor(self):
        # ...
        selected = self.tree.selection()
        survey_id_to_edit = None

        if self.current_list_type == "mine" and selected:
            item = self.tree.item(selected[0])
            # 确保选中的问卷是自己创建的
            survey_id_to_edit = item['values'][0]

        if SurveyEditorWindow:
            # 传递 sock 参数，并传递选中的 survey_id (如果存在，否则为 None，表示创建新问卷)
            SurveyEditorWindow(self.master, self.user_id, sock=self.sock, edit_survey_id=survey_id_to_edit)
        else:
            messagebox.showerror("错误", "问卷编辑器模块(Module A)未加载")
# =====================================================
# Main Application - 【已修复 sock 传递和 DashboardView 实例化】
# =====================================================
class UserSystemApp:
    def __init__(self, master):
        self.master = master
        self.master.title("问卷系统 - 综合管理")
        self.master.geometry("1000x700")

        self.current_user_id = None
        self.is_admin = False
        self.sock = None  # 【修复】添加 sock 属性

        # 登录容器
        self.login_frame = tk.Frame(master)
        self.login_frame.pack(expand=True, fill="both")

        self.create_login_view()

    def create_login_view(self):
        """创建登录/注册选项卡"""
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

        # 使用 db_utils 验证
        try:
            user = db_utils.get_user_by_login(name)

            if user:
                input_hash = pwd
                if hasattr(db_utils, 'hash_password'):
                    input_hash = db_utils.hash_password(pwd)

                db_pwd = user.get('password_hash') or user.get('password')

                if db_pwd == input_hash or db_pwd == pwd:
                    # 检查用户状态（避免禁用用户登录）
                    if user.get('user_status') == 'banned':
                        messagebox.showerror("登录失败", "您的账户已被禁用，请联系管理员。")
                        return

                    self.current_user_id = user['user_id']
                    self.is_admin = (user['user_status'] == 'admin')
                    messagebox.showinfo("登录成功", f"欢迎 {user['user_name']}")
                    self.show_dashboard()
                else:
                    messagebox.showerror("登录失败", "密码错误")
            else:
                messagebox.showerror("登录失败", "用户不存在")
        except Exception as e:
            messagebox.showerror("系统错误", f"数据库连接失败: {e}")

    def register_action(self):
        name = self.entry_reg_name.get()
        pwd = self.entry_reg_pwd.get()

        if not name or not pwd:
            messagebox.showwarning("提示", "请填写完整信息")
            return

        try:
            pwd_to_store = pwd
            if hasattr(db_utils, 'hash_password'):
                pwd_to_store = db_utils.hash_password(pwd)

            # 默认状态为 'active'
            db_utils.add_user(user_name=name, password=pwd_to_store, user_status='active', unban_time=None)
            messagebox.showinfo("注册成功", "注册成功，请登录")
        except Exception as e:
            messagebox.showerror("注册失败", f"可能用户名已存在或系统错误: {e}")

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