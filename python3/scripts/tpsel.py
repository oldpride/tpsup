#!/usr/bin/env python

import argparse
import json
import os
import sys
import tarfile
import textwrap
import time
from pprint import pformat

import tpsup.envtools
import tpsup.nettools
import tpsup.seleniumtools
import tpsup.tpsocketserver
from tpsup.modtools import run_module
from tpsup.utilbasic import tplog, tplog_exception
import tpsup.tmptools
import tpsup.tartools

prog = os.path.basename(sys.argv[0])
script_dir = os.path.dirname(sys.argv[0])

my_env = tpsup.envtools.Env()
my_env.adapt()
home_dir = my_env.home_dir
system = my_env.system

driverlog = os.path.join(home_dir, 'selenium_chromedriver.log')
# driver log on Windows must use Windows path, eg, C:/Users/tian/test.log.
# Even when we run the script from Cygwin or GitBash, we still need to use Windows path.

usage = textwrap.dedent(f"""
    batch mode
        {prog} mod_file [args]
        {prog} -modOnly mod_file1 mod_file2

    server mode
        {prog} listener_port [init_mod_file args]

    client mode
        {prog} serverHost:port server_mod_file [args]

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
    {prog}                 tpsel_base/test_google.py
    {prog} -dryrun         tpsel_base/test_google.py
    {prog} --headless      tpsel_base/test_google.py

    {prog}                 tpsel_base/test_login.py -- -u tester
    {prog} -modOnly        tpsel_base/test_google.py tpsel_base/test_login.py

    platform specifics
        in Linux, Windows GitBash
            {prog} tpsel_base/test_google.py
        in Windows, cygwin, cmd.exe, or powershell
            python {prog} tpsel_base/test_google.py

server mode examples:
    {prog}  -server 29999
    {prog}  -server 29999  tpsel_base/test_login.py -- -u tester
    {prog}  -server 29999  -base {script_dir}/tpsel_base

client mode examples:
    {prog}  -client localhost:29999 test_login.py -- -u tester
    {prog}  -client localhost:29999 -accept tar test_urlretrieve.py
    {prog}  -client localhost:29999 -accept tar test_download.py
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
    '-base', dest="base", default=None, action='store',
    help=f"in server mode, all modules asked by client are located in this place. "
         f"default to $TPSELBASE if set; otherwise, {script_dir}/tpsel_base. ")

parser.add_argument(
    '-client', dest="serverHostPort", default=None, action='store',
    help=f"run {prog} in client mode, sending the mod_files and args to server, eg, localhost:29999"
         "client mode will not start webdriver and browser"
         "default is batch mode")

parser.add_argument(
    '-key', dest="key", default=None, action='store',
    help="used in client or server mode to encrypt data communication. without it, data will not be encrypted")

parser.add_argument(
    '-accept', dest="accept", default="json", action='store',
    help="used in client to specify accept file type: json, tar. default to json")

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
key: str = args['key']  # python casting, type hint, typing hint

if verbose:
    sys.stderr.write("args =\n")
    sys.stderr.write(pformat(args) + "\n")

serverHostPort = args['serverHostPort']
if serverHostPort:

    if args['mod_file'] is None:
        sys.stderr.write("ERROR: wrong number of args. expecting mod_file")
        sys.exit(1)

    tmpdir = tpsup.tmptools.tptmp().get_nowdir()

    # this is client mode if serverHostPort is defined
    ensock = tpsup.nettools.encryptedsocket(key, host_port=serverHostPort)

    request = {
        'mod_file': args['mod_file'],
        'args': args['remainingArgs'],
        'accept': args['accept'],
    }

    request_str = json.dumps(request)
    request_bytes = bytes(request_str, "utf-8")
    tplog(f"Sending {len(request_bytes)} bytes", file=sys.stderr)
    ensock.send_and_encode(request_bytes)

    # shut down the send channel so that the other side recv() won't wait forever
    ensock.send_shutdown()

    tplog("Sent. waiting response")
    if request['accept'] == 'json':
        received_bytes = ensock.recv_and_decode(
            timeout=60)  # this needs a long wait
        tplog(f"received {received_bytes} bytes")
        received_str = str(received_bytes, 'utf-8')
        received_structure = json.loads(received_str)
        tplog(f"Received data structure: {pformat(received_structure)}")
    elif request['accept'] == 'tar':
        tar_name = os.path.join(tmpdir, "reply.tar")
        recv_size = ensock.recv_and_decode(timeout=60, file=tar_name)
        tplog(
            f"received size={recv_size}, file={tar_name}, file_size={os.path.getsize(tar_name)}")
        exception_str = None
        try:
            exception_str = tpsup.tartools.extract_tar_to_string(
                tar_name, "exception.txt")
        except KeyError:
            pass

        if exception_str:
            print(f"received exception={exception_str}")
        else:
            dir = os.path.join(my_env.home_dir, "selenium")
            tplog(f"extracting files to {dir}")
            with tarfile.open(tar_name, 'r') as tar:
                tar.extractall(dir)
    sys.exit(0)

if not args['listenerPort'] and not args['mod_file']:
    print(
        f"ERROR: {prog} in non-server mode must specify at least one mod_file", file=sys.stderr)
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
        run_module(mod_file, mod_type='file',
                   seleniumEnv=seleniumEnv, verbose=verbose)
else:
    # all optional args at the end are args to the preceding mod_file
    mod_file = args['mod_file']
    run_module(mod_file, mod_type='file', seleniumEnv=seleniumEnv,
               verbose=verbose, argList=args['remainingArgs'])

base = args['base']
if not base:
    base = my_env.environ.get('TPSEL_BASE')
if not base:
    base = os.path.join(script_dir, "tpsel_base")

listenerPort = args.get('listenerPort', None)
if (listenerPort):
    listener = tpsup.tpsocketserver.tpsocketserver(listenerPort)
    listener_max_idle = 3600
    while True:
        tplog(
            f"waiting for new client connection. will time out after {listener_max_idle} idle seconds")
        ensock = listener.accept(
            key=key, timeout=listener_max_idle)  # this timeout only only affects listener\
        if not ensock:
            tplog(f"timed out after {listener_max_idle} idle seconds")
            listener.close()
            break
        tplog(f"accepted client socket {ensock}")

        # one tmpdir for each client
        tmpdir = tpsup.tmptools.tptmp().get_nowdir()

        decoded_bytes = ensock.recv_and_decode()
        tplog(f"received {len(decoded_bytes)} bytes")
        decoded_str = ensock.in_coder.xor(decoded_bytes)
        request = json.loads(decoded_str, object_hook=dict)

        request_validated = True
        for k in ('mod_file', 'args', 'accept'):
            if not k in request:
                tplog(f"{decoded_str} missing key='{k}")
                request_validated = False
                break
        if not request_validated:
            # don't let client request to bump out our server
            ensock.close()
            continue

        result = None
        exception_str = None
        try:
            result = run_module(os.path.join(base, request['mod_file']),
                                mod_type='file', seleniumEnv=seleniumEnv,
                                verbose=verbose, argList=request['args'])
        except Exception as e:
            tplog_exception(e)
            # Exception's scope is only here, so we have to save it into a string
            exception_str = tpsup.util.print_exception(e, file=str)

        if request['accept'] == 'json':
            reply = {}
            reply['result'] = result
            reply['exception'] = exception_str

            tplog(f"reply = {pformat(reply)}")
            reply_str = json.dumps(reply)
            reply_bytes = bytes(reply_str, "utf-8")
            tplog(
                f"sending {len(reply_bytes)} bytes to client and closing connection")
            ensock.send_and_encode(reply_bytes)
            ensock.close()
        if request['accept'] == 'tar':
            tar_name = os.path.join(tmpdir, "result.tar")

            if not exception_str:
                download_dir = result
                tplog(f"creating {tar_name} from {download_dir}")
                try:
                    tpsup.tartools.create_tar_from_dir_root(
                        tar_name, download_dir)
                except Exception as e:
                    exception_str = tpsup.util.print_exception(e, file=str) + \
                        f"\ntar_name={tar_name}\ndownload_dir={download_dir}"
                    if isinstance(e, TypeError):
                        exception_str += "\n\nshould you instead use: -accept json ?"

            if exception_str:
                short_name = "exception.txt"
                tplog(
                    f"creating {tar_name} containing {short_name} form exception_str")
                tpsup.tartools.create_tar_from_string(
                    tar_name, short_name, exception_str)

            tplog(
                f"sending {tar_name}, size={os.path.getsize(tar_name)} to client and closing connection")
            ensock.send_and_encode(tar_name, data_is_file=True)
            ensock.close()


seleniumEnv.quit()
time.sleep(1)
seleniumEnv.print_running_drivers()

if args['verbose']:
    tplog(f'driverlog file {seleniumEnv.driverlog}')
    tplog(f'chromedir dir  {seleniumEnv.chromedir}')
