import socket
import threading

# 服务器 IP 和端口
HOST = '127.0.0.1'
PORT = 9000

# 启动服务器时输入模板
template = input("请输入该次问卷模板内容：\n")


# 客户端处理线程
def handle_client(conn, addr):
    print(f"客户端 {addr} 已连接")

    # 发送模板给客户端
    conn.sendall(template.encode('utf-8'))

    while True:
        try:
            data = conn.recv(1024)
            if not data:
                break
            print(f"收到来自 {addr} 的填写内容: {data.decode('utf-8')}")
        except ConnectionResetError:
            break

    conn.close()
    print(f"客户端 {addr} 已断开")


def start_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((HOST, PORT))
    server.listen(5)
    print(f"服务器启动，等待客户端连接...  ({HOST}:{PORT})")

    while True:
        conn, addr = server.accept()
        thread = threading.Thread(target=handle_client, args=(conn, addr))
        thread.start()


if __name__ == "__main__":
    start_server()
