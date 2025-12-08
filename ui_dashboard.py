# ui_dashboard.py
import tkinter as tk
from tkinter import messagebox
from module_a.ui_editor import SurveyEditorWindow  # 导入 A 的编辑器


class DashboardView(tk.Frame):
    def __init__(self, master, user_id):
        super().__init__(master)
        self.master = master
        self.user_id = user_id

        # 背景色（方便区分区域）
        self.configure(bg="#F0F0F0")

        # ============================================
        # 1. 顶部内容区域 (占满剩余空间)
        # ============================================
        self.content_frame = tk.Frame(self, bg="#FFFFFF")
        self.content_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=20, pady=20)

        # (这里放置之前的 Treeview 列表，代码略，为了突出重点先写个标签)
        tk.Label(self.content_frame, text=f"欢迎用户 {user_id} 进入主面板\n这里将显示问卷列表",
                 font=("Arial", 16), bg="white").pack(pady=50)

        # ============================================
        # 2. 底部固定边栏 (Footer)
        # ============================================
        # 使用深色背景，与主界面区分
        self.bottom_bar = tk.Frame(self, height=80, bg="#333333")
        # side=BOTTOM 确保它永远固定在最下方
        self.bottom_bar.pack(side=tk.BOTTOM, fill=tk.X)
        self.bottom_bar.pack_propagate(False)  # 禁止自动压缩高度

        # ============================================
        # 3. 底部中心的创建按钮
        # ============================================
        # 创建一个显眼的按钮
        self.create_btn = tk.Button(
            self.bottom_bar,
            text="＋ 创建问卷",
            font=("Arial", 14, "bold"),
            bg="#4CAF50",  # 绿色，非常显眼
            fg="white",  # 白字
            activebackground="#45a049",  # 点击时的颜色
            activeforeground="white",
            relief="raised",
            cursor="hand2",  # 鼠标放上去变小手
            command=self.open_editor  # 点击跳转
        )

        # 将按钮居中放置
        self.create_btn.place(relx=0.5, rely=0.5, anchor="center", width=150, height=50)

    def open_editor(self):
        """点击按钮，跳转到 A 的问卷创建界面"""
        # 使用 Toplevel 打开新窗口，保持 root 存在
        SurveyEditorWindow(self.master, self.user_id)