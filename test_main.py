import tkinter as tk
from tkinter import simpledialog, messagebox
from ui_dashboard import DashboardView
from module_b.client_socket import send_request
import threading
import json
import socket
import time

SERVER_HOST = "127.0.0.1"
SERVER_PORT = 5000

def start_dashboard(user_id: int):
    root = tk.Tk()
    root.title(f"问卷管理系统 - 用户 {user_id}")
    root.geometry("1024x768")
    root.resizable(False, False)



    # 建立 socket 与服务端通信
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((SERVER_HOST, SERVER_PORT))

    app = DashboardView(root, user_id,sock)
    app.pack(fill=tk.BOTH, expand=True)
    # 登录消息
    login_msg = {"action": "login", "params": {"user_id": user_id}}
    sock.sendall(json.dumps(login_msg).encode("utf-8"))

    # 后台线程监听强制退出消息
    def listen_server_messages():
        try:
            sock.settimeout(0.5)  # 设置非阻塞 / 超时
            while True:
                try:
                    data = sock.recv(4096)
                    if data:
                        msg = json.loads(data.decode("utf-8"))
                        if msg.get("action") == "force_logout":
                            messagebox.showinfo("提示", "你的账号在另一界面登录，你已被强制退出")
                            root.destroy()
                            break
                except socket.timeout:
                    pass  # 轮询继续
                except Exception as e:
                    break
                time.sleep(0.1)
        finally:
            sock.close()

    threading.Thread(target=listen_server_messages, daemon=True).start()

    root.mainloop()
    sock.close()

if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()
    user_id = simpledialog.askinteger("登录", "请输入用户ID:")
    root.destroy()
    if user_id is not None:
        start_dashboard(user_id)
