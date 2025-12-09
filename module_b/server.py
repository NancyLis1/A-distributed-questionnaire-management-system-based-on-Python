# service.py
import socket
import json
import threading
import sys,os
# 让程序能找到根目录的 db_utils.py
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db_utils import *  # 原来的 db_utils

HOST = "0.0.0.0"
PORT = 5000


lock = threading.Lock()

active_users = {}  # user_id -> conn

def handle_client(conn, addr):
    try:
        data = conn.recv(65536)
        if not data:
            return

        request = json.loads(data.decode("utf-8"))
        action = request.get("action")
        params = request.get("params", {})

        # 判断是否是登录动作
        if action == "login":
            user_id = params.get("user_id")
            # 检查是否已有相同用户登录
            if user_id in active_users:
                old_conn = active_users[user_id]
                try:
                    old_conn.sendall(json.dumps({"action": "force_logout"}).encode("utf-8"))
                    old_conn.close()
                except:
                    pass
            # 保存最新的登录连接
            active_users[user_id] = conn

        # 调用 db_utils 的函数
        if not hasattr(__import__("db_utils"), action):
            response = {"error": f"Unknown action: {action}"}
        else:
            func = getattr(__import__("db_utils"), action)
            try:
                result = func(**params)
                response = {"result": result}
            except Exception as e:
                response = {"error": str(e)}

        conn.sendall(json.dumps(response).encode("utf-8"))

    except Exception as e:
        conn.sendall(json.dumps({"error": str(e)}).encode("utf-8"))
    finally:
        # 如果连接断开，清理登录状态
        for uid, c in list(active_users.items()):
            if c == conn:
                del active_users[uid]
        conn.close()

def start_server():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, PORT))
        s.listen()
        print(f"[服务启动] Listening on {HOST}:{PORT} ...")

        while True:
            conn, addr = s.accept()
            thread = threading.Thread(target=handle_client, args=(conn, addr))
            thread.start()

if __name__ == "__main__":
    start_server()
