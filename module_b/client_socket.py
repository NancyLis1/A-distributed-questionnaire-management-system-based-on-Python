# module_b/client_socket.py
import socket
import json
import time


def send_request(action: str, params: dict = None, sock=None, timeout: float = 5.0):
    """
    发送请求到服务器，并等待响应。
    采用循环接收策略，解决大数据包被截断（TCP拆包）导致的 JSON 解析错误。
    """
    if sock is None:
        raise Exception("必须传入登录 socket")

    request_data = {"action": action, "params": params or {}}

    # 设置超时 (保持你要求的短超时，因为我们通过优化逻辑来加速)
    sock.settimeout(timeout)

    try:
        # 1. 发送请求
        sock.sendall(json.dumps(request_data).encode("utf-8"))

        # 2. 循环接收响应
        buffer = b""
        chunk_size = 4096

        while True:
            try:
                # 尝试接收数据
                chunk = sock.recv(chunk_size)
                if not chunk:
                    # 连接关闭
                    if not buffer:
                        raise Exception("服务器未发送响应或连接已关闭。")
                    break  # 数据接收完毕（针对短连接），或者是异常断开

                buffer += chunk

                # 尝试解析 JSON
                # 如果数据不完整，loads 会报错，我们就继续接收下一块
                try:
                    response_str = buffer.decode("utf-8")
                    response = json.loads(response_str)
                    # 如果解析成功，说明数据完整了，跳出循环
                    break
                except json.JSONDecodeError:
                    # 数据还不完整，继续 recv
                    continue

            except socket.timeout:
                # 如果缓冲区有数据但解析失败，说明接收了一半卡住了
                if buffer:
                    raise Exception(f"数据接收不完整 (已接收 {len(buffer)} 字节)，网络超时。")
                raise Exception(f"网络超时 ({timeout}秒限制)：服务器处理过慢或网络波动。")

    except Exception as e:
        # 捕获所有网络层面的错误
        raise Exception(f"网络通信错误: {e}")

    # 3. 处理业务逻辑错误
    if "error" in response:
        raise Exception(response["error"])

    return response.get("result")