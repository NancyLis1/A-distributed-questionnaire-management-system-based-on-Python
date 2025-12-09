# client_socket.py
import socket
import json
from typing import Any, Optional

SERVER_HOST = "127.0.0.1"  # 服务端地址
SERVER_PORT = 5000         # 服务端端口

def send_request(action: str, params: Optional[dict] = None) -> Any:
    """
    发送请求给服务端，并返回结果
    action: db_utils 中函数名

    params: 函数参数字典
    """
    if params is None:
        params = {}

    request_data = {"action": action, "params": params}
    data_bytes = json.dumps(request_data).encode("utf-8")

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect((SERVER_HOST, SERVER_PORT))
        sock.sendall(data_bytes)

        # 接收完整响应
        chunks = []
        while True:
            chunk = sock.recv(4096)
            if not chunk:
                break
            chunks.append(chunk)
        response_bytes = b"".join(chunks)

    response = json.loads(response_bytes.decode("utf-8"))
    if "error" in response:
        raise Exception(response["error"])
    return response.get("result")
