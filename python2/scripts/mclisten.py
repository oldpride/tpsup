#!/usr/bin/env python2.7

# https://stackoverflow.com/questions/603852/multicast-in-python
import socket
import struct
import argparse
import sys
import textwrap
from pprint import pprint, pformat

usage = textwrap.dedent("""\
    multicast listener
    """)

examples = textwrap.dedent("""
    examples:
    mclisten.py 239.203.245.157 32539
    mclisten.py 239.203.245.254 50000
    """)

parser = argparse.ArgumentParser(
    prog=sys.argv[0],
    description=usage,
    formatter_class=argparse.RawDescriptionHelpFormatter,
    epilog=examples)

parser.add_argument(
    'group', default=None, action='store', help='multicast group, eg, 239.203.245.157')

parser.add_argument(
    'port', default=None, action='store', type=int, help='multicast port, eg 32539')

parser.add_argument(
    '-v', '--verbose', action="store_true", help='print some detail')

args = vars(parser.parse_args())

if (args['verbose']):
    print >> sys.stderr, "args ="
    print >> sys.stderr, pformat(args)

MCAST_GRP = args['group']
MCAST_PORT = args['port']

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

sock.bind((MCAST_GRP, MCAST_PORT))

mreq = struct.pack("4sl", socket.inet_aton(MCAST_GRP), socket.INADDR_ANY)

sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

print >> sys.stderr, "type Control-C to exit"

while True:
    # print sock.recv(10240)
    # https://stackoverflow.com/questions/493386/how-to-print-without-newline-or-space
    sys.stdout.write(sock.recv(10240))
