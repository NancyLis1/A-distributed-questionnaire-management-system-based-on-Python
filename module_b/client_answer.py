import socket
import tkinter as tk
import threading

HOST = '127.0.0.1'
PORT = 9000

class ClientGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("客户端问卷填写")

        self.template_label = tk.Label(self.root, text="正在连接服务器...", justify="left")
        self.template_label.pack(pady=10)

        self.entry = tk.Entry(self.root, width=50)
        self.entry.pack(pady=10)

        self.submit_button = tk.Button(self.root, text="提交填写内容", command=self.send_reply)
        self.submit_button.pack(pady=10)

        threading.Thread(target=self.connect_server, daemon=True).start()

        self.root.mainloop()

    def connect_server(self):
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client.connect((HOST, PORT))

        # 接收服务器发来的问卷模板
        template = self.client.recv(1024).decode('utf-8')
        self.template_label.config(text=f"问卷模板：\n{template}")

    def send_reply(self):
        reply = self.entry.get()
        if reply:
            self.client.sendall(reply.encode('utf-8'))
            self.entry.delete(0, tk.END)

if __name__ == "__main__":
    ClientGUI()
