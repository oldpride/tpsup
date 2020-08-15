"""
mimic socketserver.TCPServer
1. add timeout. socketserver.serve_forever() doesn't have a timeout
"""
import selectors
import socket
import sys
from typing import Union
import tpsup.nettools
from tpsup.util import tplog
from pprint import pformat

if hasattr(selectors, 'PollSelector'):
    _ServerSelector = selectors.PollSelector
else:
    _ServerSelector = selectors.SelectSelector

class tpsocketserver:
    """mimic socketserver.TCPServer
    I need a timeout in the serv_forever()"""

    def __init__(self, port: Union[str, int], address: str = '0.0.0.0', backlog:int = 5):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind((address, int(port)))
        self.socket.listen(backlog)

    def accept(self, key: str = None, timeout: int = 3600, **opt) -> Union[tpsup.nettools.encryptedsocket, None]:
        verbose = opt.get('verbose', 0)
        if verbose:
            tplog(f"waiting for new client connection. time out after {timeout} idle seconds")
        selector = _ServerSelector()
        selector.register(self.socket, selectors.EVENT_READ)
        poll_interval = 1
        waited_so_far = 0
        while waited_so_far < timeout:
            if verbose > 2:
                print("looping")
            ready = selector.select(poll_interval)
            if ready:
                (clientsocket, address) = self.socket.accept()
                if verbose:
                    tplog(f"accepted client socket {clientsocket}, address={address}")
                return tpsup.nettools.encryptedsocket(established_socket=clientsocket, key=key)
            else:
                waited_so_far += poll_interval
        return None

    def close(self):
        self.socket.close()
        self.socket = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


def main():
    print(f'sys.args={pformat(sys.argv)}')

    if len(sys.argv) < 2:
        print("usage: prog client|server")
        sys.exit(1)

    key = "abc"
    host = "localhost"
    port = '3333'

    # https://docs.python.org/3/howto/sockets.html

    if sys.argv[1] == 'client':
        data = 'hello server'

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect((host, int(port)))
            ensock = tpsup.nettools.encryptedsocket(established_socket=sock, key=key)
            ensock.send_string(data + "\n")
            ensock.send_shutdown()
            received = ensock.recv_string()

        print("Sent:     {}".format(data))
        print("Received: {}".format(received))
    elif sys.argv[1] == 'server':
        data = "hello client"
        listener = tpsocketserver(port)
        while True:
            timeout = 10
            # tplog(f"waiting for client at port {port}, will time out after {timeout} seconds")
            ensock = listener.accept(key=key, timeout=timeout)
            if not ensock:
                sys.exit(1)
            print(f"accepted client socket {ensock.socket}")
            received = ensock.recv_string()
            print("Received: {}".format(received))

            ensock.send_string(data)
            print("Sent:     {}".format(data))

            ensock.close()


if __name__ == '__main__':
    main()
