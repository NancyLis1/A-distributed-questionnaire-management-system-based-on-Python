# module_b/client_socket.py (修复版)
import socket
import json
from typing import Any, Optional

SERVER_HOST = "127.0.0.1"  # 服务端地址
SERVER_PORT = 5000  # 服务端端口


def send_request(action: str, params: dict = None, sock=None, timeout: float = 5.0):
    """
    发送请求到服务器，并等待响应。

    :param action: 请求的动作名称
    :param params: 请求参数字典
    :param sock: 已连接的 socket（必须传入）
    :param timeout: 接收超时时间（秒）。。
    """
    if sock is None:
        raise Exception("必须传入登录 socket")

    request_data = {"action": action, "params": params or {}}

    # 设置发送和接收超时时间
    sock.settimeout(timeout)

    try:
        # 1. 发送请求
        sock.sendall(json.dumps(request_data).encode("utf-8"))

        # 2. 接收响应（只接收一次数据，修复了循环接收导致固定延迟的问题）
        response_bytes = sock.recv(65536)

        if not response_bytes:
            raise Exception("服务器未发送响应或连接已关闭。")

    except socket.timeout:
        # 抛出具体的超时错误信息
        raise Exception("网络超时 (5秒限制)：接收服务器响应超时，请检查服务器是否正常。")
    except Exception as e:
        raise Exception(f"网络错误：发送或接收数据出错: {e}")

    try:
        response = json.loads(response_bytes.decode("utf-8"))
    except Exception as e:
        raw_data_snippet = response_bytes.decode('utf-8', errors='ignore')[:100]
        raise Exception(f"服务器返回数据解析错误: {e}. 原始数据片段: {raw_data_snippet}...")

    if "error" in response:
        raise Exception(response["error"])

    return response.get("result")