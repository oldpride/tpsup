import functools
import mmap
import os
import select
import socket
import sys
import time
import selectors
from pprint import pformat
from tpsup.logtools import tplog
import tpsup.env
from typing import Union

import tpsup.coder


def is_tcp_open(_host: str, _port: str):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(2)  # 2 Second Timeout
    result = sock.connect_ex((_host, int(_port)))
    sock.close()
    if result == 0:
        return True
    else:
        return False


def wait_tcps_open(host_port_list: list, timeout: int = 60):
    interval = 2
    wait_list = []
    for host_port in host_port_list:
        hp_type = type(host_port)
        if hp_type is list:
            host, port = host_port
        elif hp_type is str:
            host, port = host_port.split(':', 1)
        else:
            raise RuntimeError(
                f"unsupported type of host_port={pformat(host_port)}")
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(interval)
        item = {
            'host': host,
            'port': port,
            'sock': sock,
            'open': 0,
        }
        wait_list.append(item)
    total_time = 0
    while total_time < timeout:
        need_next_round = 0
        for item in wait_list:
            if item['open']:
                continue
            result = item['sock'].connect_ex((item['host'], int(item['port'])))
            if result == 0:
                item['sock'].close()
                item['open'] = 1
                print(f"{item['host']}:{item['port']} is open")
            else:
                need_next_round += 1
        if not need_next_round:
            print("all open")
            return True
        total_time += interval
        time.sleep(2)
    print(f"total_time={total_time}")
    for item in wait_list:
        if not item['open']:
            print(f"{item['host']}:{item['port']} is not open")
            item['sock'].close()
    print(f"not all connections open within {timeout} seconds")
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

    # python class doesn't support multiple constructors
    def __init__(self, key: str, established_socket: socket.socket = None, host_port: str = None, maxtry: int = 5,
                 try_interval: int = 3, **opt):
        if established_socket:
            self.socket = established_socket
        elif host_port:
            host, port = host_port.split(':')
            if not port:
                raise RuntimeError(
                    f"bad format at host_port='{host_port}'; expected host:port")
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            if sock:
                for i in range(0, maxtry):
                    try:
                        sock.connect((host, int(port)))
                        # tplog(f"connected to {sock}")
                        # __init__ connected to <socket.socket fd=3, family=AddressFamily.AF_INET,
                        # type=SocketKind.SOCK_STREAM, proto=0, laddr=('127.0.0.1', 36690), raddr=('127.0.0.1', 29999)>
                        laddr = sock.getsockname()
                        raddr = sock.getpeername()
                        tplog(
                            f"connected: local {laddr[0]}:{laddr[1]}, remote {raddr[0]}:{raddr[1]}")
                        tplog(
                            f"connected: local {laddr[0]}:{laddr[1]}, remote {raddr[0]}:{raddr[1]}")
                        self.socket = sock
                        break
                    except Exception as e:
                        tplog(
                            f'{i + 1} try out of {maxtry} failed to connect: {e}', file=sys.stderr)
                        if i + 1 < maxtry:
                            tplog(
                                f'will retry after {try_interval}', file=sys.stderr)
                            time.sleep(try_interval)
                        else:
                            raise RuntimeError(
                                f"failed to connect to {host}:{port} in {maxtry} tries")
            else:
                raise RuntimeError(socket.error)
        else:
            raise RuntimeError(
                "neither established_socket nor host_port specified")

        if key is None or key == '':
            key = None
        self.key = key

        self.in_coder = tpsup.coder.Coder(key)
        self.out_coder = tpsup.coder.Coder(key)

    def send_string(self, string: str, coding: str = 'utf-8', **opt) -> None:
        self.send_and_encode(string.encode(coding), **opt)

    def recv_string(self, coding: str = 'utf-8', **opt) -> str:
        """ size is max size"""
        return self.recv_and_decode().decode(coding)

    def send_shutdown(self):
        self.socket.shutdown(socket.SHUT_WR)

    def recv_shutdown(self):
        self.socket.shutdown(socket.SHUT_RD)

    def close(self):
        self.socket.close()
        self.socket = None
        self.in_coder = None
        self.out_coder = None

    # python socket has no flush()
    #     https: // stackoverflow.com / questions / 4407835 / python - socket - flush

    def recv_and_decode(self, timeout: int = 6, maxsize=1024 * 1024 * 1024, file: str = None, **opt) -> Union[
            bytes, int]:
        """ this is actually use unblocked recv() to re-implement a blocked recv().
        The possible benefits:
        - sock.recv(buffer_size)'s buffer_size is limited, we can use a loop to recv() bigger file. In this
        loop pattern, socket.settimeout() looks awkward. socket.settimeout() seems better for
        small data
        - decrypt the incoming data with smaller chunks, ie, in buffer_size
        """

        if file:
            # receive data will write to this file
            fh = open(file, 'wb')
        else:
            fh = None

        # https://docs.python.org/3/library/socket.html

        # getblocking()/setblocking() is implemented by gettimeout()/settimeout. no getblocking() before 3.7
        saved_timeout = self.socket.gettimeout()
        # saved_blocking = self.socket.getblocking() this only available when version >= 3.7

        # unblock
        # None: blocking mode; 0: non-blocking mode; positive floating: timeout mode.
        self.socket.setblocking(0)

        polling_interval = 1
        wait_so_far = 0
        total_size = 0
        received_bytearray = bytearray()
        while wait_so_far < timeout:
            # last arg is timeout in seconds
            ready = select.select([self.socket], [], [], polling_interval)
            if ready[0]:
                data = self.socket.recv(4096)
                # there may be exceptions here
                if data == b'':
                    tplog(f"Remote connection is closed during our recv()")
                    break

                if fh:
                    fh.write(self.in_coder.xor(data))
                else:
                    received_bytearray.extend(self.in_coder.xor(data))

                total_size += len(data)
                if total_size > maxsize:
                    tplog(
                        f"Received {total_size} bytes already exceeded maxsize {maxsize}. Stopped receiving.")
                    break
            else:
                # time.sleep(polling_interval)  # no need sleep here if we already blocked at select()
                wait_so_far += polling_interval
        if fh:
            fh.close()
        if wait_so_far >= timeout:
            tplog(f"recv() timed out after {wait_so_far} seconds")
        tplog(f"Received total {total_size} bytes")

        # getblocking()/setblocking() is implemented by gettimeout()/settimeout. no getblocking() before 3.7
        self.socket.settimeout(saved_timeout)
        # self.socket.setblocking(saved_blocking) # restoring blocking setting

        if file:
            return total_size
        else:
            return bytes(received_bytearray)

    def send_and_encode(self, data: Union[bytes, str], data_is_file: bool = False, timeout: int = 6, **opt) -> int:
        """ this is actually use unblocked send() to re-implement a blocked sendall().
        The possible benefits:
        - add encryption
        """

        file = None
        fd = None
        if data_is_file:
            file = data
            size = os.path.getsize(file)
            fd = os.open(file, os.O_RDWR)  # fd is int
            data = mmap.mmap(fd, size, access=mmap.ACCESS_READ)
            # tplog(f"data type = {type(data)}")  #

        # https://docs.python.org/3/library/socket.html
        #         socket.send() vs socket.sendall()
        #
        #         socket.send(bytes[, flags])
        #         Send data to the socket. Returns the number of bytes sent. Applications are responsible
        #         for checking that all data has been sent; if only some of the data was transmitted, the application
        #         needs to attempt delivery of the remaining data.
        #
        #         socket.sendall(bytes[, flags])
        #         Send data to the socket. Unlike send(), this method continues to
        #         send data from bytes until either all data has been sent or an error occurs. None is returned on success. On
        #         error, an exception is raised, and there is no way to determine how much data, if any, was successfully sent.

        saved_timeout = self.socket.gettimeout()
        # saved_blocking = self.socket.getblocking() this only available when version >= 3.7

        # unblock
        # None: blocking mode; 0: non-blocking mode; positive floating: timeout mode.
        self.socket.setblocking(0)
        # this is the same as self.socket.settimeout(0)

        polling_interval = 1
        wait_so_far = 0
        total_sent = 0
        data_length = len(data)

        while total_sent < data_length:
            buffer_size = 4096
            new_end = total_sent + buffer_size
            if new_end > data_length:
                new_end = data_length
                buffer_size = new_end - total_sent

            buffer_bytes = self.out_coder.xor(data[total_sent:new_end])

            buffer_sent = 0
            while buffer_sent < buffer_size:
                ready = select.select([], [self.socket], [], polling_interval)
                if ready[1]:
                    sent = self.socket.send(buffer_bytes[buffer_sent:])
                    # there may be exceptions here
                    if sent == 0:
                        tplog(f"Remote connection is closed during our send()")
                        break
                    buffer_sent += sent
                    total_sent += sent
                else:
                    wait_so_far += polling_interval
                    if wait_so_far >= timeout:
                        tplog(f"send() timed out after {wait_so_far} seconds")
                        break
            else:
                # the above loop did NOT break = the above loop condition was False = the loop ended naturally
                # python's way to break nested loop (double loop)
                # https://stackoverflow.com/questions/653509/breaking-out-of-nested-loops
                continue
            break  # the above loop DID break = the above loop condition was still True = the loop didn't end naturally

        if fd:
            os.close(fd)

        missing = data_length - total_sent
        if missing > 0:
            tplog(
                f"Sent total {total_sent} bytes. failed to send {missing} bytes")
        else:
            tplog(f"Sent all {total_sent} bytes")

        # getblocking()/setblocking() is implemented by gettimeout()/settimeout. no getblocking() before 3.7
        self.socket.settimeout(saved_timeout)
        # self.socket.setblocking(saved_blocking) # restoring blocking setting

        return total_sent


def test_wait_tcps_open():
    tcps = [
        'localhost:135',  # normally open on Windows
        'localhost:445',  # normally open on Windows
        'localhost:4723',  # appium server
        'localhost:22',  # normally open on Linux
    ]
    result = wait_tcps_open(tcps, timeout=2)
    print(f"result={pformat(result)}")


def test_encryptsocket():
    print(f'sys.args={pformat(sys.argv)}')

    if len(sys.argv) < 2:
        print('''
usage: prog client|server|clientfile|serverfile"

use two terminals: one run client and one run server

        ''')
        sys.exit(1)

    key = "abc"
    host = "localhost"
    port = '3333'

    env = tpsup.env.Env()
    tmpdir = env.tmpdir

    # https://docs.python.org/3/howto/sockets.html

    if sys.argv[1] == 'client':
        data = 'hello server'
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            ensock = encryptedsocket(key, host_port=f"{host}:{port}")
            ensock.send_string(data + "\n")
            ensock.send_shutdown()
            received = ensock.recv_string()
        print("Sent:     {}".format(data))
        print("Received: {}".format(received))
    elif sys.argv[1] == 'server':
        data = "hello client"
        serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # 0.0.0.0 means all interfaces
        serversocket.bind(('0.0.0.0', int(port)))
        serversocket.listen(5)
        while True:
            print(
                f"waiting for client at port {port}. Control-C won't work on Windows until client connects")
            (clientsocket, address) = serversocket.accept()
            print(f"accepted client socket {clientsocket}")
            ensock = encryptedsocket(key, established_socket=clientsocket)
            received = ensock.recv_string()
            print("Received: {}".format(received))
            ensock.send_string(data)
            print("Sent:     {}".format(data))
            ensock.close()
            break  # because control-c doesn't interrupt accept() on windows, we only test one loop
    elif sys.argv[1] == 'clientfile':
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            ensock = encryptedsocket(key, host_port=f"{host}:{port}")
            recv_file = f"{env.tmpdir}/test_client.txt"
            send_file = "runtest.bash"
            print(
                f"sent send_file={send_file}, file_size={os.path.getsize(send_file)}")
            size = ensock.send_and_encode(send_file, data_is_file=True)
            ensock.send_shutdown()
            print(f"sent size={size}")
            print(f"receiving")
            size = ensock.recv_and_decode(file=recv_file)
            print(
                f"received recv_file={recv_file}, size={size}, file_size={os.path.getsize(recv_file)}")
            ensock.close()
    elif sys.argv[1] == 'serverfile':
        serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # 0.0.0.0 means all interfaces
        serversocket.bind(('0.0.0.0', int(port)))
        serversocket.listen(5)
        while True:
            print(
                f"waiting for client at port {port}. Control-C won't work on Windows until client connects")
            (clientsocket, address) = serversocket.accept()
            print(f"accepted client socket {clientsocket}")
            ensock = encryptedsocket(key, established_socket=clientsocket)
            recv_file = f"{env.tmpdir}/test_server.txt"
            send_file = "csvtools_test.csv"
            size = ensock.recv_and_decode(file=recv_file)
            print(
                f"received recv_file={recv_file}, size={size}, file_size={os.path.getsize(recv_file)}")
            print(
                f"sent send_file={send_file}, file_size={os.path.getsize(send_file)}")
            size = ensock.send_and_encode(send_file, data_is_file=True)
            print(f"sent size={size}")
            ensock.close()
            break  # because control-c doesn't interrupt accept() on windows, we only test one loop


def main():
    test_wait_tcps_open()
    # test_encryptsocket()


if __name__ == '__main__':
    main()
