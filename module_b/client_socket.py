# module_b/client_socket.py
import socket
import json
import threading
from typing import Any, Optional

SERVER_HOST = "127.0.0.1"
SERVER_PORT = 5000


class ClientContext:
    """
    统一管理当前客户端状态
    """
    def __init__(self):
        self.business_sock: Optional[socket.socket] = None
        self.kicked: bool = False
        self.lock = threading.Lock()

    def mark_kicked(self):
        with self.lock:
            self.kicked = True
            if self.business_sock:
                try:
                    self.business_sock.close()
                except:
                    pass
                self.business_sock = None


client_ctx = ClientContext()

# Control Socket（只监听）
def start_control_listener(user_id: int, on_kicked):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((SERVER_HOST, SERVER_PORT))

    bind_msg = {
        "action": "bind_control",
        "params": {"user_id": user_id}
    }
    sock.sendall(json.dumps(bind_msg).encode("utf-8"))

    def listen():
        while True:
            try:
                data = sock.recv(4096)
                if not data:
                    break

                msg = json.loads(data.decode("utf-8"))
                if msg.get("type") == "kicked":
                    client_ctx.mark_kicked()
                    on_kicked(msg.get("reason", "账号在其他地方登录"))
                    break
            except:
                break
        sock.close()

    threading.Thread(target=listen, daemon=True).start()

# Business Request
def send_request(action: str, params: Optional[dict] = None, sock: Optional[socket.socket] = None,
                 timeout: float = 5.0) -> Any:
    if client_ctx.kicked:
        raise Exception("当前账号已在其他地方登录")
    if sock is None:
        raise Exception("必须传入 business socket")

    sock.settimeout(timeout)
    request = {"action": action, "params": params or {}}

    try:
        # 发送请求时增加换行符，方便服务端处理
        msg = json.dumps(request).encode("utf-8")
        sock.sendall(msg)

        # 接收响应：针对长连接的优化处理
        # 简单逻辑：一次性尝试接收足够大的数据，或者直到解析出 JSON
        data = sock.recv(65536)  # 适当加大缓冲区
        if not data:
            raise Exception("服务器关闭了连接")

        response = json.loads(data.decode("utf-8"))

        if response.get("type") == "kicked":
            client_ctx.mark_kicked()
            raise Exception("账号在其他地方登录")

        if "error" in response:
            raise Exception(response["error"])

        return response.get("result")

    except socket.timeout:
        raise Exception("网络超时：服务器响应超时")
    except Exception as e:
        raise Exception(f"网络错误: {e}")