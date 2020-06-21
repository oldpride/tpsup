import socket


def is_tcp_open(_host: str, _port: str):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(2)  # 2 Second Timeout
    result = sock.connect_ex((_host, int(_port)))
    if result == 0:
        return True
    else:
        return False
