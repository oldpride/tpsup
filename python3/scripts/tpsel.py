#!/usr/bin/env python

import argparse
import json
import os
import select
import socket
import socketserver
import sys
import textwrap
from pprint import pformat
import tpsup.env
import tpsup.seleniumtools
import tpsup.coder
import tpsup.nettools
from tpsup.util import run_module, tplog, print_exception, tplog_exception
import traceback
import time

prog = os.path.basename(sys.argv[0])

my_env = tpsup.env.Env()
my_env.adapt()
home_dir = my_env.home_dir
system = my_env.system

driverlog = home_dir + '/selenium_chromedriver.log'
# driver log on Windows must use Windows path, eg, C:/Users/tian/test.log.
# Even when we run the script from Cygwin or GitBash, we still need to use Windows path.

usage = textwrap.dedent(f"""
    batch mode
        {prog} mod_file [args]
        {prog} -modOnly mod_file1 mod_file2

    server mode
        {prog} listener_port [init_mod_file args]

    client mode
        {prog} serverHost:port mod_file [args]

    run selenium test modules
    
    +----------+      +--------------+     +----------------+
    | selenium +----->+ chromedriver +---->+ chrome browser +---->internet
    +----------+      +--------------+     +----------------+
    
    selenium will always start a chromedriver locally.

    If there is a chrome browser already started at the host:port, this script will start a chromedriver
    and direct the chromedriver to connect to the host:port. After the script is done, the chromedriver
    will be automatically shut down but the browser will live on.

    If there is no browser at the host:port, this script will start a chromedriver, and the chromedriver
    will start a chrome browser which will listen at the host:port. chromedriver will shut down the
    browser when the script is done. The shutdown call is automatically registered, and so far no 
    successful practice to disable it.

    To manually start a local browser at port 19999
        From Linux,
            /usr/bin/chromium-browser --no-sandbox --disable-dev-shm-usage --window-size=960,540 \
            --user-data-dir=~/chrome_test --remote-debugging-port=19999 
        From Cygwin or GitBash,
            'C:/Program Files (x86)/Google/Chrome/Application/chrome.exe' --window-size=960,540 \
            --user-data-dir=C:/users/$USERNAME/chrome_test --remote-debugging-port=19999
        From cmd.exe, (have to use double quotes)
            "C:/Program Files (x86)/Google/Chrome/Application/chrome.exe" --window-size=960,540 \
            --user-data-dir=C:/users/%USERNAME%/chrome_test --remote-debugging-port=19999

    For Linux
        chromedriver should be in the path or at ~
        chromium-browser should be in path
    
    For Windows, 
        chromedriver.exe should be in the PATH or at C:/users/<current_user>
        chrome.exe       should be in the PATH or at C:/Program Files (x86)/Google/Chrome/Application

    """)

examples = textwrap.dedent(f""" 
batch mode examples:
    {prog}                 tpsel_test_google.py
    {prog} -dryrun         tpsel_test_google.py
    {prog} --headless      tpsel_test_google.py

    {prog}                 tpsel_test_login.py -- -u tester
    {prog} -modOnly        tpsel_test_google.py tpsel_test_login.py

    platform specifics
        in Linux, Windows GitBash
            {prog} tpsel_test_google.py
        in Windows, cygwin, cmd.exe, or powerhell
            python {prog} tpsel_test_google.py

server mode examples:
    {prog}  -server 29999
    {prog}  -server 29999  tpsel_test_login.py

client mode examples:
    {prog}  -client localhost:29999  tpsel_test_login.py -- -u tester
    """)

parser = argparse.ArgumentParser(
    prog=sys.argv[0],
    epilog=examples,
    description=usage,
    # formatter_class=argparse.RawTextHelpFormatter, # this honors \n but messed up indents
    formatter_class=argparse.RawDescriptionHelpFormatter
)

parser.add_argument(
    '--headless', action='store_true', default=False,
    help="headless")

parser.add_argument(
    '-v', '--verbose', default=0, action="count",
    help='verbose level: -v, -vv, -vvv')

default_hostport = "localhost:19999"

parser.add_argument(
    '-hp', '--host_port', default=default_hostport,
    help="port of the browser. default to " + f"{default_hostport}")

parser.add_argument(
    '-ba', '--browserArgs', action="append", default=[],
    help='extra args to browser command, eg, -ba proxy-pac-url=http://pac.abc.net. can set multiple times.')

parser.add_argument(
    '-driver', dest="driver", default="chromedriver", action='store',
    help="driver executable file, eg, 'chromedriver78', default 'chromedriver', must be in PATH. Can also use path, "
         "for example, "
         "./chromedriver. we use this in case chromedriver and chrome browser's version mismatch.")

parser.add_argument(
    '-driverlog', dest="driverlog", default=driverlog, action='store',
    help="driver log, driver log on Windows must use Windows path, eg, C:/Users/tian/test.log. Even when we run the "
         "script from Cygwin or GitBash, we still need to use Windows path. "
         f"On this host, default to {driverlog}")

parser.add_argument(
    '-dryrun', '--dryrun', dest='dryrun', action='store_true', default=False, help='dryrun mode')

parser.add_argument(
    '-server', dest="listenerPort", default=None, action='store',
    help=f"run {prog} in server mode at this listener port, eg, 29999"
         "server will first run the mod_files before accept client"
         "default is batch mode")

parser.add_argument(
    '-client', dest="serverHostPort", default=None, action='store',
    help=f"run {prog} in client mode, sending the mod_files and args to server, eg, localhost:29999"
         "client mode will not start webdriver and browser"
         "default is batch mode")

parser.add_argument(
    '-key', dest="key", default=None, action='store',
    help="used in client or server mode to encrypt data communication. without it, data will not be encrypted")

parser.add_argument(
    '-modOnly', '--modOnly', dest='modOnly', action='store_true', default=False, help='remaining args are mod files')

parser.add_argument(
    'mod_file', default=None, nargs='?', action='store',
    help='python file')

parser.add_argument(
    # args=argparse.REMAINDER indicates optional remaining args and stored in a List
    'remainingArgs', nargs=argparse.REMAINDER,
    help='remaining args. Can be mod_file if -modOnly set, or default to args to the preceding mod_file, start with --')

args = vars(parser.parse_args())
# default to parse command line args. we can also parse any list: args = vars(parser.parse_args(['hello', 'world'))

verbose = args['verbose']
key = args['key']

if verbose:
    sys.stderr.write("args =\n")
    sys.stderr.write(pformat(args) + "\n")

# python socket programming
# https://docs.python.org/3/howto/sockets.html

serverHostPort = args['serverHostPort']
if serverHostPort:
    # this is client mode is serverHostPort is defined
    host, port = serverHostPort.split(':')
    maxtry = args.get("maxtry", 5)
    interval = args.get("interval", 3)
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        ensock = None
        for i in range(0, maxtry):
            try:
                sock.connect((host, int(port)))
                ensock = tpsup.nettools.encryptedsocket(sock, key)
                break
            except Exception as e:
                tplog(f'{i+1} try out of {maxtry} failed to connect: {e}', file=sys.stderr)
                if i+1 < maxtry:
                    tplog(f'will retry after {interval}', file=sys.stderr)
                    time.sleep(interval)
                else:
                    break
        if ensock:
            request = {}

            # read the entire file
            with open(args['mod_file'], 'r') as f:
                request['module'] = f.read()

            request['args'] = args['remainingArgs']
            request['accept'] = 'json'

            request_str = json.dumps(request)
            request_bytes = bytes(request_str, "utf-8")
            tplog(f"Sending {len(request_bytes)} bytes", file=sys.stderr)
            ensock.sendall(request_bytes)

            # https://stackoverflow.com/questions/35113723/when-why-to-use-s-shutdownsocket-shut-wr
            # shut down the send channel so that the other side recv() won't wait forever
            ensock.socket.shutdown(socket.SHUT_WR)

            tplog("Sent. waiting response")
            received = str(ensock.recv(1024), "utf-8")
            tplog(f"Received: {len(received)}")

    sys.exit(0)

if not args['listenerPort'] and not args['mod_file']:
    print(f"ERROR: {prog} in non-server mode must specify at least one mod_file", file=sys.stderr)
    # parser.print_help()   # long version help
    parser.print_usage()    # short version help
    sys.exit(1)

seleniumEnv = tpsup.seleniumtools.SeleniumEnv(**args)

driver = seleniumEnv.get_driver()

if driver is None and not args['dryrun']:
    sys.exit(1)

if args['modOnly']:
    # all optional args at the end are module files
    for mod_file in [args['mod_file']] + args['remainingArgs']:
        run_module(mod_file, mod_is_file=True, seleniumEnv=seleniumEnv, verbose=verbose)
else:
    # all optional args at the end are args to the preceding mod_file
    mod_file = args['mod_file']
    run_module(mod_file, mod_is_file=True, seleniumEnv=seleniumEnv, verbose=verbose, argList=args['remainingArgs'])

listenerPort = args.get('listenerPort', None)
if (listenerPort):
    data = "hello client"
    # this is server mode
    # 0.0.0.0 means all interfaces
    serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # bind the socket to a public host, and a well-known port
    serversocket.bind(('0.0.0.0', int(listenerPort)))  # 0.0.0.0 means all interfaces
    # become a server socket
    serversocket.listen(5)
    listener_max_idle = 3600
    while True:
        serversocket.settimeout(listener_max_idle)  # this only affects serversocket
        try:
            tplog(f"waiting for new client connection. time out after {listener_max_idle} idle seconds")
            (clientsocket, address) = serversocket.accept()
        except socket.timeout as e:
            tplog(print_exception(e, file=str))
            tplog(f"server exit after {listener_max_idle} idle seconds")
            serversocket.close()
            sys.exit(0)
        tplog(f"accepted client socket {clientsocket}")

        ensock = tpsup.nettools.encryptedsocket(clientsocket, key)
        decoded_bytes = ensock.recv_all(timeout=6)
        decoded_str = str(decoded_bytes, 'utf-8')
        request = json.loads(decoded_str, object_hook=dict)

        for k in ('module', 'args', 'accept'):
            if not k in request:
                tplog(f"{decoded_str} missing key='{k}")
                sys.exit(1)

        # don't let client request to bump out our server
        result = None
        exception = None
        try:
            result = run_module(request['module'], seleniumEnv=seleniumEnv, verbose=verbose, argList=request['args'])
        except Exception as e:
            tplog_exception(e)
            exception = e

        if request['accept'] == 'json':
            reply = {}
            reply['result'] = result
            reply['exception'] = e
            reply_str = json.dumps(reply)
            reply_bytes = bytes(reply_str, "utf-8")





seleniumEnv.quit()
time.sleep(1)
seleniumEnv.print_running_drivers()

if args['verbose']:
    tplog(f'driverlog file {seleniumEnv.driverlog}')
    tplog(f'chromedir dir  {seleniumEnv.chromedir}')
