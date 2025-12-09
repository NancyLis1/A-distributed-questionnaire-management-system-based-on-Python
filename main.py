# main.py
import tkinter as tk
from ui_dashboard import DashboardView
from db_proxy import send_request
import tkinter as tk
from tkinter import messagebox  # ✅ 需要单独导入

import threading
import json

def main():
    root = tk.Tk()
    root.title("问卷管理系统")
    root.geometry("1024x768")
    root.resizable(False, False)

    # 模拟当前登录用户
    current_user_id = 1

    # 加载主面板
    app = DashboardView(root, current_user_id)
    app.pack(fill=tk.BOTH, expand=True)

    # 后台线程监听强制退出消息
    def listen_server_messages(sock, root):
        try:
            while True:
                data = sock.recv(4096)
                if not data:
                    break
                msg = json.loads(data.decode("utf-8"))
                if msg.get("action") == "force_logout":
                    messagebox.showinfo("提示", "你的账号在另一界面登录，你已被强制退出")
                    root.destroy()  # 直接关闭界面
                    break
        except:
            pass

    threading.Thread(target=listen_server_messages, daemon=True).start()

    root.mainloop()

if __name__ == "__main__":
    main()
