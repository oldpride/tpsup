#!/usr/bin/env python2.7

# http://python-future.org/compatible_idioms.html
from __future__ import print_function  # pip install future
import yaml  # pip install PyYaml
import os
import re
import sys
import argparse
import textwrap
from pprint import pprint, pformat
import subprocess
import ConfigParser
from subprocess import Popen, PIPE, STDOUT
import time

prog = os.path.basename(sys.argv[0])

# https://stackoverflow.com/quest ions/4934 806/how-can-i-f ind-scripts-directory-with-python
def get_script_path():
    return os.path.dirname(os.path.realpath(sys.argv[0]))

script_path = get_script_path()
default_config = script_path + "/<env>.yaml"

def parse_config(file):
    Config = ConfigParser()
    Config.read(file)
    return Config

usage = textwrap.dedent("""\
    check environment
    """)

examples = textwrap.dedent("""
Examples:
    chk_env.py pp
    chk_env.py pp -a APP1
    chk_env.py pp -a APP1 -c Component1
    """)

parser = argparse.ArgumentParser(
    prog=sys.argv[0],
    description = usage,
    formatter_class = argparse.RawDescriptionHelpFormatter,
    epilog = examples)

parser.add_argument(
    '-conf', '--config', dest="config_file", default=default_config,
    action='store', type=str,
    help="env config, default to " + default_config)

parser.add_argument(
    '-a', '--app', dest="app", default=None,
    action='store', type=str,
    help="app name, default to all apps in " + default_config)

parser.add_argument(
    '-c', '--component', dest="component", default=None,
    action='store', type=str,
    help="component name, default to all components defined for the app")

parser.add_argument(
    '-m', '--mai1Summary', dest="addresses", default=None,
    action='store', type=str,
    help="email addresses, separated by comma, default not to send email")

parser.add_argument(
    '--sendAlert', action="store_true",
    help='send out alert email when some instance is down. '
         'default not to send out alert email.')

parser.add_argument(
    dest="env", default=None,
    action='store', type=str,
    help="env: uat, pp, or prod")

parser.add_argument(
    '-v', '--verbose', action="store_true",
    help='print some detail')

args = vars(parser.parse_args())

if (args['verbose']):
    print ("args =", file=sys.stderr)
    print (pformat(args), file=sys.stderr)

env = args['env']
config_file = args['config_file']

if config_file == default_config:
    config_file = config_file.replace('<env>', env)

if not os.path.exists(config_file):
    print('config file' + config_file + ' not found', file=sys.stderr)
    sys.exit(1)

#https://pyyaml.org/wiki/PyYAMLDocumentation
stream = file(config_file, 'r')
Config = yaml.load(stream)

if (args['verbose']):
    print("Config =", file=sys.stderr)
    print(yaml.dump(Config), file=sys.stderr)
    print(pformat(Config), file=sys.stderr)

results = []
results.append(['Application', 'Component', 'Login', 'Host', 'Status'])

AllRecepient = {}

for app in Config.keys():
    if args['app'] == None or args['app'] == app:
        for component in Config[app].keys():
            if args['component'] == None or args['component'] == component:
                command = Config[app][component]['command']
                host_line = Config[app][component]['host']
                login = Config[app][component]['login']
                recepient = Config[app][component]['recepient']

                if 'expect' in Config[app][component]:
                    expect = Config[app][component]['expect']
                else:
                    expect = None

                hosts = host_line.split(",")

                for host in hosts:
                    print('')
                    print('app=' + app + ' component=' + component + ' host=' + host)

                    cmd_args = ['ssh', '-q', '-o', 'StrictHostKeyChecking=no',
                                login + '@' + host,
                                '. ~/.profile; [ -f ~/.bash_profile ] && . ~/.bash_profile;'
                                + command]
                    print(cmd_args)
                    print('expect=' + str(expect))
                    # https://docs.python.org/2/1ibrary/subprocess.html
                    # https://stackoverflow.com/quest ions/2 867513 8/python-check-
                    # output-faiIs-with-ex it-status-1-but-popen-works-for-same-command
                    output =None

                    try:
                        output = subprocess.check_output(cmd_args)
                    except Exception as ex:
                        print('Error:' + repr(ex))
                        if output == None:
                            output = 'Error:' + repr(ex)
                    else:
                        print(output)

                    if expect != None:
                        if re.search(expect, output):
                            print('match')
                            results.append([app, component, login, host, 'up'])
                        else:
                            print('mismatch')
                            results.append([app, component, login, host, 'down'])
                            for r in recepient.split(","):
                                if args['sendAlert']:
                                    AllRecepient[r] = 1

print(pformat(results), file=sys.stderr)

if args['addresses'] != None:
    for address in args['addresses'].split(','):
        AllRecepient[address] = 1

Recepients = AllRecepient.keys()

if Recepients:
    address_string = ','.join(Recepients)

    print('sending mail to ' + address_string)

    html = '''<html>\n
        <head>
        <meta http-equiv="Content-Type" content="text/html; charset=iso-8859-1">
        </head>\n
        <body bgcolor=" white" ><title></title>\n
        <table cellpadding="1" cellspacing="1" border="1" bordercolor="black">\n'''

    down_count = 0

    for row in results:
        html += '<tr>'
        for cell in row:
            if cell == 'down':
                html += '<td bgcolor="red">' + cell + '</td>'
                down_count += 1
            elif cell == 'up':
                html += '<td bgcolor="green">' + cell + '</td>'
            else:
                html += '<td>' + cell + '</td>'
        html += '</tr>\n'
    html += '</tablex/bodyx/html>\n'

    message = 'To:	' + address_string + '\n'
    message += 'Subject:	' + 'PP Env Check (' + str(down_count) + ' down) ' \
               + time.strftime('%Y/%m/%d-%H:%M:%S', time.localtime(time.time())) + '\n'
    cmd_args = ['/usr/sbin/sendmail', '-t']
    message += 'Content-Type: text/html\n'
    message += html

    print(message, file=sys.stderr)

    pi = subprocess.Popen(cmd_args, stdout=PIPE, stdin=PIPE, stderr=PIPE)
    pi.communicate(input=message)[0]
