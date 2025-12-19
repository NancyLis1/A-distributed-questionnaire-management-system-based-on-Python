import socket
import json
import threading
import sys, os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db_utils import *

HOST = "0.0.0.0"
PORT = 5000

lock = threading.Lock()
active_users = {}
# user_id -> {
#   "business": conn,
#   "control": conn
# }

def handle_client(conn, addr):
    user_id = None
    socket_type = None  # "business" or "control"
    try:
        while True:
            data = conn.recv(65536)
            if not data:
                break
            raw_str = data.decode("utf-8")
            try:
                request = json.loads(raw_str)
            except Exception:
                print(f"[DEBUG] 解析 JSON 失败: {raw_str}")
                continue
            action = request.get("action")
            params = request.get("params", {})

            if action == "bind_control":
                user_id = params.get("user_id")
                socket_type = "control"

                with lock:
                    if user_id not in active_users:
                        active_users[user_id] = {}

                    active_users[user_id]["control"] = conn
                    print(f"[DEBUG] 用户 {user_id} 绑定 control socket")

                # control socket 只监听，不回业务响应
                continue

            elif action == "login":
                user_id = params.get("user_id")
                socket_type = "business"
                print(f"[DEBUG] 用户 {user_id} 尝试登录 (business)")

                with lock:
                    if user_id not in active_users:
                        active_users[user_id] = {}

                    # 如果已有旧登录 → 强制下线
                    old_control = active_users[user_id].get("control")
                    old_business = active_users[user_id].get("business")

                    if old_control:
                        try:
                            print(f"[DEBUG] 强制下线用户 {user_id}")
                            old_control.sendall(json.dumps({
                                "type": "kicked",
                                "reason": "账号在其他地方登录"
                            }).encode("utf-8"))
                        except Exception as e:
                            print(f"[DEBUG] 发送踢下线失败: {e}")

                    if old_business:
                        try:
                            old_business.close()
                        except:
                            pass

                    active_users[user_id]["business"] = conn
                    print(f"[DEBUG] 用户 {user_id} business 登录成功")

                # 给客户端一个正常登录响应
                conn.sendall(json.dumps({
                    "action": "login_ok",
                    "user_id": user_id
                }).encode("utf-8"))


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

                conn.sendall(json.dumps(response).encode("utf-8"))

    except Exception as e:
        print(f"[DEBUG] 异常: {e}")


    finally:
        with lock:
            if user_id and user_id in active_users:
                if socket_type:
                    if active_users[user_id].get(socket_type) == conn:
                        print(f"[DEBUG] 清理 {socket_type} socket: user_id={user_id}")
                        del active_users[user_id][socket_type]

                # 如果两个 socket 都没了，删用户
                if not active_users[user_id]:
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
