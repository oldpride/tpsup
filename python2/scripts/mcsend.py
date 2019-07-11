#!/usr/bin/env python2.7

# https://stackoverflow.com/questions/603852/multicast-in-python
import socket
import struct
import argparse
import sys
import textwrap
from pprint import pprint, pformat

usage = textwrap.dedent("""\
    multicast sender
    """)

examples = textwrap.dedent("""
    examples:
    mcsend.py 239.203.245.157 32539
    mcsend.py 239.203.245.254 50000
    """)

parser = argparse.ArgumentParser(prog=sys.argv[0], description=usage,
                                 formatter_class=argparse.RawDescriptionHelpFormatter, epilog=examples);

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
# regarding socket.IP_MULTICAST_TTL
#
# for all packets sent, after two hops on the network the packet will not
# be re-sent/broadcast (see https://www.tldp.org/H0WT0/Multicast-H0WT0-6.html)
MULTICAST_TTL = 2

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, MULTICAST_TTL)

print >> sys.stderr, "type Control-C or Control-D to exit"

# https://st ackoverflow.com/questions/1450393/how-do-you-read-from-stdin-in-python
while 1:
    try:
        line = sys.stdin.readline()
    except KeyboardInterrupt:
        break

    if not line:
        break
    # print "copy " + line

    sock.sendto(line, (MCAST_GRP, MCAST_PORT))
