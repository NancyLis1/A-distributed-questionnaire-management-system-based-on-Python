# client_socket.py
import socket
import json
from typing import Any, Optional

SERVER_HOST = "127.0.0.1"  # 服务端地址
SERVER_PORT = 5000  # 服务端端口


def send_request(action: str, params: dict = None, sock=None, timeout: float = 5.0):
    """
    发送请求到服务器，并等待响应。

    此函数使用 64KB 缓冲区和消息定界符 (\n) 循环接收数据，
    以确保在接收大响应时不会因为缓冲区太小而误判为网络错误。

    :param action: 请求的动作名称
    :param params: 请求参数字典
    :param sock: 已连接的 socket（必须传入）
    :param timeout: 接收超时时间（秒）
    """
    if sock is None:
        raise Exception("必须传入登录 socket")

    request_data = {"action": action, "params": params or {}}

    try:
        # 1. 发送请求
        request_msg = json.dumps(request_data).encode("utf-8")
        sock.sendall(request_msg)
    except Exception as e:
        raise Exception(f"发送请求到服务器失败: {e}")

    # 2. 设置接收超时时间
    sock.settimeout(timeout)

    # 3. 循环接收数据，直到找到定界符 '\n' 或超时
    response_bytes = b''
    try:
        while True:
            # 每次尝试接收最大的缓冲区 (64KB)
            chunk = sock.recv(65536)

            if not chunk:
                # 服务器主动关闭连接
                break

            response_bytes += chunk

            # 检查是否接收到消息定界符 (\n)
            if b'\n' in response_bytes:
                # 只取第一个完整的 JSON 包（定界符之前的部分）
                response_bytes = response_bytes.split(b'\n', 1)[0]
                break

    except socket.timeout:
        # 超时发生，尝试解析已接收的数据
        pass
    except Exception as e:
        raise Exception(f"接收数据出错: {e}")

    # 4. 最终检查和解析
    if not response_bytes:
        # 如果超时发生且未收到任何数据，则抛出错误
        raise Exception("网络超时或连接已关闭，未收到服务器响应。")

    try:
        response = json.loads(response_bytes.decode("utf-8"))
    except Exception as e:
        # 如果解析失败，可能是数据不完整或格式错误
        raise Exception(f"服务器返回的数据格式错误或不完整: {e} - 原始数据长度: {len(response_bytes)}")

    # 5. 检查服务器是否返回了错误
    if "error" in response:
        # 统一处理服务器端的业务逻辑错误
        raise Exception(f"服务器错误: {response['error']}")

    # 6. 返回结果
    return response.get("result")

# 登录和监听不需要 send_request，它们在 UI 逻辑中单独处理，保持不变