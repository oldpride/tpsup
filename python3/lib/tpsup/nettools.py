import socket
import sys
import time

import tpsup.coder


def is_tcp_open(_host: str, _port: str):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(2)  # 2 Second Timeout
    result = sock.connect_ex((_host, int(_port)))
    if result == 0:
        return True
    else:
        return False


class TpConn:
    def __init__(self, sock: socket.socket, key: str = None, **opt):
        self.socket = sock
        if key is None or key == '':
            key = None
        self.key = key

        self.in_coder = tpsup.coder.Coder(key)
        self.out_coder = tpsup.coder.Coder(key)

    def send(self, data: bytes, size: int = -1, **opt) -> int:
        ''' mimic socket.send(bytes[,flags])
        https://docs.python.org/3/library/socket.html
        '''
        self.socket.send(self.out_coder.xor(data, size=size))

    def sendString(self, string: str) -> int:
        self.send(string.encode('utf-8'))

    def recv(self, size, **opt) -> bytes:
        '''socket.recv(bufsize[, flags])
        https://docs.python.org/3/library/socket.html
        size is the max size
        '''
        return self.in_coder.xor(self.socket.recv(size))

    def recvString(self, size, **opt) -> str:
        ''' size is max size'''
        return self.recv(size).decode('utf-8')

    def close(self):
        self.socket.close()
        self.socket = None

    # python socket has no flush()
    #   https: // stackoverflow.com / questions / 4407835 / python - socket - flush


def connect(host: str, port: int, **opt) -> TpConn:
    key = opt.get("encode", None)
    maxtry = opt.get("maxtry", 5)
    interval = 3
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        for i in range(0,maxtry):
            try:
                sock.connect((host, int(port)))
                conn = TpConn(sock, key)
                return conn
            except Exception as e:
                print(f'{i+1} try out of {maxtry} failed to connect: {e}', file=sys.stderr)
                if i+1 < maxtry:
                    print(f'will retry after {interval}', file=sys.stderr)
                else:
                    break
            time.sleep(interval)


def main():
    connect('localhost', 9999)

if __name__ == '__main__':
    main()


