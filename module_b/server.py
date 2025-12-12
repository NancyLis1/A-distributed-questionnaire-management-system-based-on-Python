import socket
import json
import threading
import sys, os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db_utils import *

HOST = "0.0.0.0"
PORT = 5000

lock = threading.Lock()
active_users = {}  # user_id -> conn

def handle_client(conn, addr):
    user_id = None
    try:
        while True:
            data = conn.recv(65536)
            if not data:
                break

            request = json.loads(data.decode("utf-8"))
            action = request.get("action")
            params = request.get("params", {})

            if action == "login":
                user_id = params.get("user_id")
                print(f"[DEBUG] 用户 {user_id} 尝试登录")

                with lock:
                    if user_id in active_users:
                        old_conn = active_users[user_id]
                        try:
                            print(f"[DEBUG] 用户 {user_id} 已登录，发送强制下线")
                            logout_msg = json.dumps({"action": "force_logout"}) + '\n'
                            old_conn.sendall(logout_msg.encode("utf-8"))
                        except Exception as e:
                            print(f"[DEBUG] 发送强制下线失败: {e}")

                    active_users[user_id] = conn
                    print(f"[DEBUG] 用户 {user_id} 登录成功，保存连接")
                # 这里不用 break，保持循环接收

            else:
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

                # 🚀 修正：添加 \n 作为消息定界符
                response_to_send = json.dumps(response) + '\n'
                conn.sendall(response_to_send.encode("utf-8"))

    except Exception as e:
        print(f"[DEBUG] 异常: {e}")

    finally:
        with lock:
            if user_id and active_users.get(user_id) == conn:
                del active_users[user_id]
        print(f"[DEBUG] 关闭连接: {addr}")
        conn.close()

def start_server():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, PORT))
        s.listen()
        print(f"[服务启动] Listening on {HOST}:{PORT} ...")

        while True:
            conn, addr = s.accept()
            print(f"[DEBUG] 新客户端连接: {addr}")
            thread = threading.Thread(target=handle_client, args=(conn, addr))
            thread.start()

if __name__ == "__main__":
    start_server()
