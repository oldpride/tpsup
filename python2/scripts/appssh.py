#!/usr/bin/env python2.7

# http://python-future.org/compatible_idioms.html
from __future__ import print_function  # pip install future
import yaml # pip install PyYaml
import os
import sys
import argparse
import textwrap
import time
import re
import ConfigParser
from pprint import pprint, pformat

prog = os.path.basename(sys.argv[0])

# https://stackoverflow.com/quest ions/4934 806/how-can-i-find-scripts-directory-with-python

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
    examples:
    - log onto a APP1's component1's host
    appssh.py pp APP1 component1
    
    - run a remote command 'hostname -s' on APP1's component1' host
    appssh.py pp APP1 component1 -- hostname -s
    
    - list all available connections
    appssh.py pp list conn
    
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
    dest="env", default=None,
    action='store', type=str,
    help="env: uat, pp, or prod")

parser.add_argument(
    dest="app", default=None,
    action='store', type=str,
    help="app name, defined in " + default_config)

parser.add_argument(
    dest="component", default=None,
    action='store', type=str,
    help="component of an app. " + default_config)

parser.add_argument(
    '-v', '--verbose', action="store_true",
    help='print some detail')

parser.add_argument(
    dest="cmd", nargs='*',
    help="remote command")

args = vars(parser.parse_args())

if (args['verbose']):
    print ("args =", file=sys.stderr)
    print (pformat(args), file=sys.stderr)

env = args['env']
app = args['app']
config_file = args['config_file']
component = args['component']

if config_file == default_config:
    config_file = script_path + "/" + env + ".yaml"

if not os.path.exists(config_file):
    print('config file ' + config_file + ' not found', file=sys.stderr)
    sys.exit(1)

# https://pyyaml.org/wiki/PyYAMLDocumentation
stream = file(config_file, 'r')
Config = yaml.load(stream)

if (args['verbose']):
    print("Config =", file=sys.stderr)
    print(yaml.dump(Config), file=sys.stderr)
    print(pformat(Config), file=sys.stderr)

if app == 'list':
    for app in sorted(Config.keys()):
        for component in Config[app].keys():
            print(app + '/' + component)
            host_line = Config[app][component]['host']
            login = Config[app][component]['login']

            hosts = sorted(host_line.split(","))
            for host in hosts:
                ssh = 'ssh ' + login + '@' + host
            print('     cmd = ' + ssh)
    sys.exit(0)

def print_app(C):
    for app in sorted(Config.keys()):
        for component in Config[app].keys():
            host_line = Config[app][component]['host']
            login = Config[app][component]['login']
            print(app + '/' + component + '/' + login + '@' + host_line)

if not (app in Config.keys()):
    print('app="' + app + '" is not defined in ' + config_file, file=sys.stderr)
    print('Defined apps:', file=sys.stderr)
    for app in sorted(Config.keys()):
        print('   ' + app, file=sys.stderr)
    print('', file=sys.stderr)  #print a blank line
    sys.exit(1)

if not (component in Config[app].keys()):
    print('component="' + component + '" is not defined in app='
          + app + ' in ' + config_file,
          file=sys.stderr)
    print('Defined components for app=' + app + ':', file=sys.stderr)
    for component in Config[app].keys():
        print('   ' + component, file=sys.stderr)
    print('', file=sys.stderr)
    sys.exit(1)

host_line = Config[app][component]['host']
login = Config[app][component]['login']
hosts = sorted(host_line.split(","))
BuildlnVar = {}
yyyyMMDDHHMMSS = time.strftime('%Y%m%d%H%M%S', time.localtime())
BuildlnVar['YYYY'] = yyyyMMDDHHMMSS[:4]
BuildlnVar['mm'] = yyyyMMDDHHMMSS[4:6]
BuildlnVar['dd'] = yyyyMMDDHHMMSS[6:8]
BuildlnVar['HH'] = yyyyMMDDHHMMSS[8:10]
BuildlnVar['MM'] = yyyyMMDDHHMMSS[10:12]
BuildlnVar['SS'] = yyyyMMDDHHMMSS[12:]
def SubVariables(input_array, InstanceVar):
    output_array = []

    for s0 in input_array:
        s = s0
        for loop in [0, 1]:
            for var in BuildlnVar.keys():
                s = re.sub(r'%' + var + '%', str(BuildlnVar[var]), s)
            for var in InstanceVar.keys():
                s = re.sub(r'%' + var + '%', InstanceVar[var], s)
        output_array.append(s)
    return output_array

for host in hosts:
    InstanceVar = {}

    InstanceVar['app'] = app
    InstanceVar['component'] = component
    InstanceVar['host'] = host
    InstanceVar['login'] = login

    for optional in ['log']:
        if optional in Config[app][component]:
            InstanceVar[optional] = Config[app][component][optional]

    cmd_list = ['ssh']
    cmd_list.append('-o StrictHostKeyChecking=no')
    cmd_list.append('-q')
    cmd_list.append(login + '@' + host)

    if args['cmd']:
        new_cmd = SubVariables(args['cmd'], InstanceVar)
        cmd_list.extend(new_cmd)

    if (args['verbose']):
        print(pformat(cmd_list), file=sys.stderr)

    os.execv('/usr/bin/ssh', cmd_list)
