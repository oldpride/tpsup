#!/usr/bin/env python

import sys

from tpsup.tpsocketserver import tpsocketserver
from tpsup.util import tplog

listenerPort = 9999
port = listenerPort
key = 'abc'
# listener = tpsup.tpsocketserver.tpsocketserver(listenerPort)
# listener_max_idle = 10
# while True:
#     ensock = listener.accept(key="", timeout=listener_max_idle)  # this timeout only only affects listener\
#     if not ensock:
#         listener.close()
#         sys.exit(0)
#     tplog(f"accepted client socket {ensock}")

data = "hello client"
with tpsocketserver(port) as listener:
    while True:
        timeout = 10
        tplog(f"waiting for client at port {port}, will time out after {timeout} seconds")
        ensock = listener.accept(key=key, timeout=timeout)
        if not ensock:
            sys.exit(1)
        print(f"accepted client socket {ensock.socket}")
        received = ensock.recv_string()
        print("Received: {}".format(received))

        ensock.send_string(data)
        print("Sent:     {}".format(data))

    ensock.close()
