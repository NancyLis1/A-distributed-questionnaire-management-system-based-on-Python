# client_socket.py
import socket
import json
from typing import Any, Optional

SERVER_HOST = "127.0.0.1"  # 服务端地址
SERVER_PORT = 5000         # 服务端端口

def send_request(action: str, params: dict = None, sock=None, timeout: float = 5.0):
    """
    发送请求到服务器，并等待响应。

    :param action: 请求的动作名称
    :param params: 请求参数字典
    :param sock: 已连接的 socket（必须传入）
    :param timeout: 接收超时时间（秒）
    """
    if sock is None:
        raise Exception("必须传入登录 socket")

    request_data = {"action": action, "params": params or {}}
    sock.sendall(json.dumps(request_data).encode("utf-8"))

    # 设置接收超时时间
    sock.settimeout(timeout)

    chunks = []
    try:
        while True:
            chunk = sock.recv(4096)
            if not chunk:
                break
            chunks.append(chunk)
    except socket.timeout:
        # 超时后尝试解析已接收到的数据
        if not chunks:
            raise Exception("接收服务器响应超时，请检查服务器是否正常")
        # 可能接收到部分数据，但仍尝试解析
    except Exception as e:
        raise Exception(f"接收数据出错: {e}")

    response_bytes = b"".join(chunks)
    try:
        response = json.loads(response_bytes.decode("utf-8"))
    except Exception as e:
        raise Exception(f"解析服务器响应失败: {e}")

    if "error" in response:
        raise Exception(response["error"])
    return response.get("result")
