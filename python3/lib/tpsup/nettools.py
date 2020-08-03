import functools
import select
import socket
import sys
import time
from pprint import pformat
from tpsup.util import tplog

import tpsup.coder


def is_tcp_open(_host: str, _port: str):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(2)  # 2 Second Timeout
    result = sock.connect_ex((_host, int(_port)))
    if result == 0:
        return True
    else:
        return False

# abandoned the design to subclass socket.socket
# reason:
#     1. for server, we need to init the coder after accept() created client socket, not at __init__().
#        because each client socket needs to have its own coder (specifically code index).
#     2. for client, not that big deal as client only has one server, but it still looks better to
#        set up the coder after connect() succeeds.
#
# Using inheritance was for the following reason:
#
# class TpSocket(socket.socket):
#     """a wrapper socket to provide encryption
#
#         I first tried to replace the instance method like below,
#             def sendall(data: bytes, flags: int = 0) -> None:
#                 return sock.socket.sendall(out_coder.xor(data), flags)
#             def recv(size: int, flags: int = 0) -> bytes:
#                 return in_coder.xor(sock.socket.recv(size, flags))
#             sock.sendall = sendall
#             sock.recv = recv
#         but got error:
#             AttributeError: 'socket' object attribute 'sendall' is read-only
#         Therefore, i switched to use inheritance
#     """
#
#     def __init__(self, key: str = None, *args):
#         if key is None or key == '':
#             key = None
#         self.key = key
#         self.in_coder = tpsup.coder.Coder(key)
#         self.out_coder = tpsup.coder.Coder(key)
#         super().__init__(*args)
#     def sendall(self, data: bytes, size: int = -1) -> None:
#         super().sendall(self.out_coder.xor(data, size=size))
#     def recv(self, size: int, flags=0) -> bytes:
#         return self.in_coder.xor(super().recv(size))


class encryptedsocket:
    """ encrypt an existing socket"""
    def __init__(self, sock: socket.socket, key: str = None, **opt):
        if not sock:
            raise RuntimeError('socket is not initialized yet')
        self.socket = sock
        if key is None or key == '':
            key = None
        self.key = key

        self.in_coder = tpsup.coder.Coder(key)
        self.out_coder = tpsup.coder.Coder(key)

    def sendall(self, data: bytes, size: int = -1) -> None:
        ''' mimic socket.sendall(bytes[,flags])
        https://docs.python.org/3/library/socket.html
        '''
        self.socket.sendall(self.out_coder.xor(data, size=size))
        '''
        socket.send() vs socket.sendall()

        socket.send(bytes[, flags]) 
        Send data to the socket. Returns the number of bytes sent. Applications are responsible
        for checking that all data has been sent; if only some of the data was transmitted, the application
        needs to attempt delivery of the remaining data.

        socket.sendall(bytes[, flags]) 
        Send data to the socket. Unlike send(), this method continues to 
        send data from bytes until either all data has been sent or an error occurs. None is returned on success. On 
        error, an exception is raised, and there is no way to determine how much data, if any, was successfully sent. 
        '''

    def send_string(self, string: str) -> None:
        self.sendall(string.encode('utf-8'))

    def recv(self, size: int, flags=0) -> bytes:
        """socket.recv(bufsize[, flags])
        https://docs.python.org/3/library/socket.html
        size is the max size
        """
        return self.in_coder.xor(self.socket.recv(size))



    def recv_string(self, size) -> str:
        """ size is max size"""
        return self.recv(size).decode('utf-8')

    def close(self):
        self.socket.close()
        self.socket = None
        self.in_coder = None
        self.out_coder = None

    # python socket has no flush()
    #   https: // stackoverflow.com / questions / 4407835 / python - socket - flush

    def recv_all(self, timeout: int = 6, **opt) -> bytes:
        """ this is actually use unblocked recv() to re-implement a blocked recv().
        The possible benefits:
        - sock.recv(size)'s size is limited, we can use a loop to recv() bigger file. In this
        loop pattern, socket.settimeout() looks awkward. socket.settimeout() seems better for
        small data
        """

        # getblocking()/setblocking() is implemented by gettimeout()/settimeout. no getblocking() before 3.7
        saved_timeout = self.socket.gettimeout()
        # saved_blocking = self.socket.getblocking()

        # unblock
        self.socket.setblocking(0)

        sleep_between_polling = 1
        wait_so_far = 0
        received_bytearray = bytearray()
        while wait_so_far < timeout:
            ready = select.select([self.socket], [], [], 1)  # timeout is 0 but we will sleep later
            if ready[0]:
                data = self.socket.recv(4096)
                if data == b'':
                    tplog(f"client connection is closed")
                    break
                # there may be other scenarios we need to handle, for example, The other side has reset
                # the socket. You'll get an exception.
                received_bytearray.extend(self.in_coder.xor(data))
            else:
                time.sleep(sleep_between_polling)
                wait_so_far += sleep_between_polling
        if wait_so_far >= timeout:
            tplog(f"recv() timed out after {wait_so_far} seconds, did not reach EOF of client socket")
        else:
            tplog(f"reached EOF of client socket")
        tplog(f"received total {len(received_bytearray)} bytes")

        # getblocking()/setblocking() is implemented by gettimeout()/settimeout. no getblocking() before 3.7
        self.socket.settimeout(saved_timeout)
        # self.socket.setblocking(saved_blocking) # restoring blocking setting

        return bytes(received_bytearray)


def main():
    print(f'sys.args={pformat(sys.argv)}')

    if len(sys.argv) < 2:
        print("usage: prog client|server")
        sys.exit(1)

    key="abc"
    host="localhost"
    port='3333'

    # https://docs.python.org/3/howto/sockets.html

    if sys.argv[1] == 'client':
        data = 'hello server'

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect((host, int(port)))
            ensock = encryptedsocket(sock, key)
            ensock.sendall(bytes(data + "\n", "utf-8"))
            # Receive data from the server and shut down
            received = str(ensock.recv(1024), "utf-8")

        print("Sent:     {}".format(data))
        print("Received: {}".format(received))
    elif sys.argv[1] == 'server':
        data = "hello client"
        # create an INET, STREAMing socket
        serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # bind the socket to a public host, and a well-known port
        serversocket.bind(('0.0.0.0',int(port)))  # 0.0.0.0 means all interfaces
        # become a server socket
        serversocket.listen(5)
        while True:
            # accept connections from outside
            (clientsocket, address) = serversocket.accept()
            print(f"accepted client socket {clientsocket}")
            ensock = encryptedsocket(clientsocket, key)
            ensock.sendall(bytes(data + "\n", "utf-8"))
            # Receive data from the server and shut down
            received = str(ensock.recv(1024), "utf-8")

            print("Sent:     {}".format(data))
            print("Received: {}".format(received))
            ensock.close()


if __name__ == '__main__':
    main()
