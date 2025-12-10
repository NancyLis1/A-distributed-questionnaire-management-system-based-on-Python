# main.py
import tkinter as tk
from ui_dashboard import DashboardView


def main():
    # 1. 创建唯一的根窗口
    root = tk.Tk()
    root.title("问卷管理系统")

    # 2. 统一设定窗口大小 (1024x768)
    # 获取屏幕尺寸以居中显示（可选），这里先固定大小
    root.geometry("1024x768")
    root.resizable(False, False)  # 建议固定大小，防止布局错乱

    # 3. 模拟当前登录用户 (实际应从登录界面传过来)
    current_user_id = 1

    # 4. 加载主面板 (Dashboard)
    app = DashboardView(root, current_user_id)
    app.pack(fill=tk.BOTH, expand=True)

    root.mainloop()


if __name__ == "__main__":
    main()