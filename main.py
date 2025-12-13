# main.py
import tkinter as tk
import sys
import os

try:
    # 获取当前文件的目录
    current_dir = os.path.dirname(os.path.abspath(__file__))
    sub_dir_name = "module_c"  # <-- 请根据你的实际子目录名修改
    sub_dir_path = os.path.join(current_dir, sub_dir_name)

    # 检查路径是否存在，并添加到 Python 搜索路径
    if os.path.isdir(sub_dir_path):
        if sub_dir_path not in sys.path:
            sys.path.append(sub_dir_path)
    else:
        pass
except Exception as e:
    print(f"路径添加失败: {e}")

try:
    from user_system_tkinter import UserSystemApp
except ImportError:
    print("仍然无法导入 'user_system_tkinter'，请检查子目录名称或项目结构。")
    sys.exit(1)


def main():
    # 1. 创建唯一的根窗口
    root = tk.Tk()
    root.title("问卷管理系统")

    # 2. 统一设定窗口大小
    root.geometry("1000x700")
    root.resizable(True, True)

    # 3. 实例化 UserSystemApp
    app = UserSystemApp(root)

    root.mainloop()


if __name__ == "__main__":
    main()