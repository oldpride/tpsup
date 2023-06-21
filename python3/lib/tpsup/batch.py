import re

import shlex
import functools
import inspect
import io
import os
import sys
import traceback
from time import strftime, gmtime
import time
# from tpsup.modtools import run_module, load_module
from pprint import pformat, pprint
import importlib
from tpsup.util import convert_to_uppercase
import tpsup.tptmp
from datetime import datetime
from shlex import split
from typing import Union, List, Dict
from tpsup.exectools import exec_into_globals


def exec_simple(source):
    return exec_into_globals(source, globals(), locals())

# global vars needed for exec()
# our_cfg = None


def parse_cfg(cfg_file: str = None, **opt):
    verbose = opt.get('verbose', 0)

    # global vars needed for exec()
    global our_cfg

    with open(cfg_file, 'r') as f:
        source = f.read()

    exec_simple(source)

    if verbose:
        print(f'after exec, our_cfg = {pformat(our_cfg)}')

    # our_cfg = asdict(mod.our_cfg)

    parse_dict_cfg_sub = parse_dict_cfg

    module = our_cfg.get('module', None)

    if module is not None:
        imported = importlib.import_module(module)
        if hasattr(imported, 'tpbatch_parse_dict_cfg'):
            parse_dict_cfg_sub = imported.parse_dict_cfg

    our_cfg = parse_dict_cfg_sub(our_cfg, **opt)

    return our_cfg


def parse_dict_cfg(dict_cfg: type = dict, **opt):
    # convert keys to uppercase
    for attr in ['keys', 'suits']:
        if dict_cfg.get(attr, None) is not None:
            dict_cfg[attr] = convert_to_uppercase(
                dict_cfg[attr], ConvertKey=True)

    for attr in ['aliases', 'keychains']:
        if dict_cfg.get(attr, None) is not None:
            dict_cfg[attr] = convert_to_uppercase(
                dict_cfg[attr], ConvertKey=True, ConvertValue=True)

    keys = sorted(dict_cfg.get('keys', []))
    keys_string = ' '.join(keys)
    suits = dict_cfg.get('suits', {})

    suits_string = os.linesep
    for name, suit in suits.items():
        section = f'      {name}{os.linesep}'
        for k, v in sorted(suit.items()):
            section += f"         '{k}' : '{v}'{os.linesep}"
        suits_string += section

    aliases = []
    for k, v in dict_cfg.get('aliases', {}).items():
        aliases.append(f"'{k}' : '{v}'")
    aliases_string = ','.join(aliases)

    usage_detail = f'''
    keys: {keys_string}
    
    aliases: {aliases_string}
    
    suits: {suits_string}
    
    keys/aliases/suits/keychains are case-insensitive but values are case sensitive
'''

    if 'YYYYMMDD' in keys:
        today = datetime.today().strftime('%Y%m%d')
        usage_detail += f'{os.linesep}   yyyyymmdd is default to {today}'

    dict_cfg['usage_detail'] = usage_detail

    return dict_cfg


def parse_input(input: Union[str, List], all_cfg: dict, **opt):
    # water-fall
    # 1. use the parser from cfg.py
    # 2. use the parser from 'module' attribute
    # 3. use the default parser in this module

    if not (parse_input_sub := globals().get("parse_input_sub", None)):  # check function existence
        parse_input_sub = parse_input_default_way

    # # 2nd method to check function existence
    # global parse_input_sub
    # try:
    #     parse_input_sub
    # except NameError:
    #     parse_input_sub = parse_input_default_way

    if module := all_cfg.get('module', None):
        imported = importlib.import_module(module)
        if hasattr(imported, 'tppatch_parse_dict_cfg'):
            parse_input_sub = imported.tppatch_parse_dict_cfg

    return parse_input_sub(input, all_cfg, **opt)  # this set 'known' in caller


def parse_input_default_way(input: Union[str, List], all_cfg: dict, **opt):
    keys = all_cfg.get('keys', {})
    aliases = all_cfg.get('aliases', {})
    suits = all_cfg.get('suits', {})
    keychains = all_cfg.get('keychains', {})

    input_array = []
    if type(input) is list:
        input_array = input
    else:
        input_array = shlex.split(input)
    known = {}

    for pair in (input_array):
        if re.match(r'^(any|check)$', pair):
            continue

        m = re.match(r'^(.+?)=(.+)$', pair)
        if m:
            # convert key to uppercase
            (key, value) = m.groups()
            key = key.upper()

            if key == 'S' or key == 'SUIT':
                suitname = value.upper()
                suit = suits.get(suitname, None)
                if suit:
                    if opt.get('verbose', None):
                        print(
                            f"loading suit={suitname} {pformat(suit)}", file=sys.stderr)
                    for k2, v2 in suit.items():
                        if known.get(k2, None) is None:
                            # suit never overwrites known
                            known[k2] = v2
                    continue
                else:
                    raise RuntimeError(f'unknown suit={suitname}')
                continue

            key2 = aliases.get(key, None)
            if key2 is not None:
                if opt.get('verbose', None):
                    print(
                        f'converted alias={key} to key={key2}', file=sys.stderr)
                known[key2] = value
                continue

            if key in keys.keys():
                known[key] = value
                continue
            else:
                raise RuntimeError(
                    f'key={key} in pair="{pair}" is not allowed')
        raise RuntimeError(
            f'bad format at pair="{pair}", expected key=value format')

    if keys.get('YYYYMMDD', None):
        today = datetime.today().strftime('%Y%m%d')
        known['TODAY'] = today
        if known.get('YYYYMMDD', None) is None:
            # don't overwrite
            known.setdefault('YYYYMMDD', today)

    for k, v in keys.items():
        if known.get(k, None) is None:
            # don't overwrite
            known[k] = v

    for k, v in keychains.items():
        if known.get(k, None) is None:
            # don't overwrite
            known[k] = known.get(v, None)

    for k in keys.keys():
        if known.get(k, None) is None:
            raise RuntimeError(
                f'key={k} is still not defined after parsing input={pformat(input)}')

    return known


my_cfg = None


def set_all_cfg(given_cfg: Union[str, Dict], **opt):
    global my_cfg
    if type(given_cfg) == 'str':
        cfg_file = given_cfg
        my_cfg = parse_cfg(cfg_file, **opt)
    else:
        my_cfg = given_cfg


def get_all_cfg(**opt):
    global my_cfg
    if my_cfg is None:
        raise RuntimeError(f'my_cfg is not defined yet')
    return my_cfg


def parse_batch(given_cfg: Union[str, Dict], batch: Union[str, List], **opt):
    set_all_cfg(given_cfg, **opt)
    all_cfg = get_all_cfg(**opt)

    parsed_batch = []
    print(f"parse_batch: type(batch)={type(batch)}")
    if type(batch) == str:
        filename = batch
        with open(filename, 'r') as fh:
            for line in fh:
                if re.match(r'^\s*$', line):
                    continue
                if re.match(r'^\s*#', line):
                    continue

                if opt.get('verbose', None) is not None:
                    print(f'parsing line: {line}', file=sys.stderr)

                args = shlex.split(line)  # split a line like bash command line

                if opt.get('verbose', None) is not None:
                    print(f'parsed, args={pformat(args)}', file=sys.stderr)

                parsed_batch.append(args)
    else:
        parsed_batch = batch

    if not parsed_batch:
        raise RuntimeError(f'no input parsed from batch = {pformat(batch)}')
    elif opt.get('verbose', 0):
        print(f'parsed_batch = {pformat(parsed_batch)}', file=sys.stderr)

    for input in parsed_batch:
        # just validate input syntax, trying to avoid aborting in the middle of a batch.
        # therefore, we don't keep the result
        discarded = parse_input(
            input, all_cfg, verbose=opt.get('verbose', None))

    return parsed_batch


def run_batch(given_cfg: Union[str, dict], batch: list, **opt):
    # command line args coming in through **opt
    verbose = opt.get('verbose', 0)

    if verbose:
        print(f'run_batch: opt = {pformat(opt)}', file=sys.stderr)
        print()
        print(f'run_batch: given_cfg = {pformat(given_cfg)}', file=sys.stderr)
        print()
        print(f'run_batch: batch = {pformat(batch)}', file=sys.stderr)
        print()

    parsed_batch = parse_batch(given_cfg, batch, **opt)

    set_all_cfg(given_cfg, **opt)
    all_cfg = get_all_cfg(**opt)

    cfg_opt = all_cfg.get('opt', {})

    opt2 = {**cfg_opt, **opt}  # combine dicts/kwargs

    record = opt2.get('record', None)
    record_keys = []
    seen_record = set()
    record_ofh = None
    if record:
        record_keys = record.split(',')
        record_file = opt2.get('record_file', None)
        if record_file is None:
            # both always return tpbatch.py
            #   script_name = os.path.basename(sys.argv[0])
            #   script_name = os.path.basename(
            #     inspect.getframeinfo(sys._getframe(1)).filename)
            # I'd like to use the cfg file name, which is passed from tpbatch.py
            script_name = os.path.basename(opt2.get('cfg_file', 'unknown.txt'))

            dailydir = tpsup.tptmp.tptmp().get_dailydir()
            record_file = f'{dailydir}/{script_name.replace(".py", ".txt")}'
        print("record_file = ", record_file, file=sys.stderr)
        # check whether record_file exists
        if os.path.exists(record_file):
            with open(record_file, 'r') as ifh:
                whole_file = ifh.read()
                record_lines = whole_file.split('\n')
                for line in record_lines:
                    seen_record.add(line)
        record_ofh = open(record_file, 'a')
    elif record_file:
        raise RuntimeError(f'record_file is defined but record_keys is not')
    elif record_keys:
        raise RuntimeError(f'record_keys is defined but record_file is not')

    init_resources(all_cfg, **opt2)

    if opt.get('verbose', 0) > 1:
        print(f'all_cfg = {pformat(all_cfg)}', file=sys.stderr)
        print(f'opt2 = {pformat(opt2)}', file=sys.stderr)

    pre_checks = all_cfg.get('pre_checks', [])
    for pc in pre_checks:
        check = pc['check']
        if not eval(check):
            raise RuntimeError(
                f'pre_check="{check}" failed, suggestion="{pc.get("suggestion", None)}"')
        elif verbose:
            print(f'pre_check="{check}" passed')

    # verbose implies show_progress
    show_progress = verbose or opt.get(
        'show_progress', 0) or all_cfg.get('show_progress', 0)

    total = len(parsed_batch)
    i = 0
    total_time = 0
    last_time = time.time()
    end_time = None

    if show_progress:
        print(f'{os.linesep}--------------- batch begins, total={total} ---------------------', file=sys.stderr)

    for input in parsed_batch:
        i = i+1
        if show_progress:
            print(
                f'{os.linesep}---- running with input {i} of {total} ----', file=sys.stderr)
            print(f'input = {pformat(input)}', file=sys.stderr)

        known = parse_input(input, all_cfg, verbose=verbose)

        if verbose:
            print(
                f'after parsed input, known = {pformat(known)}', file=sys.stderr)

        if record:
            record_string = resolve_record_keys(record_keys, known)
            if record_string in seen_record:
                print(
                    f'already seen record, skipping: {record_string}', file=sys.stderr)
                continue
            else:
                seen_record.add(record_string)
                record_ofh.write(record_string + '\n')

        code_sub = None
        if code := globals().get("code", None):  # check function existence
            code_sub = code
        else:
            module = all_cfg.get('module', None)
            if module:
                imported = importlib.import_module(module)
                if hasattr(imported, 'code'):
                    code_sub = imported.code

        if code_sub:
            code_sub(all_cfg, known, **opt2)
        else:
            print(
                f'function code is not defined in cfg or driver module, therefore, not run', file=sys.stderr)

        if show_progress:
            now = time.time()
            duration = now - last_time
            total_time = total_time + duration
            average = total_time / i
            print(
                f'round {i} duration={int(duration)}, total={int(total_time)}, avg={int(average)}', file=sys.stderr)

    if record_ofh:
        record_ofh.close()

    if show_progress or verbose:
        print(f'{os.linesep}---- batch ends ----', file=sys.stderr)

    if not opt.get('no_post_batch', 0):
        if post_batch := globals().get("post_batch", None):
            post_batch(all_cfg, known, **opt2)

    return


def resolve_record_keys(keys, known):
    values = [known.get(k.upper(), '') for k in keys]  # upper case keys
    record_string = ','.join(values)
    return record_string


def init_resources(all_cfg: Dict, **opt):
    if all_cfg.get('resources', None) is None:
        return
    resources = all_cfg['resources']

    for k, res in resources.items():
        if res.get('enabled', 1) == 0:
            continue
        if res.get('init_resource', 1) == 0:
            # if not initiate it now, we pass back function name and params, so that
            # caller can initiate it at another time

            # this is the way to copy **kwargs
            kwargs = {}
            kwargs.update(opt)
            kwargs['driver_cfg'] = res['cfg']

            resources[k]['driver_call'] = {
                "method": res['method'],
                "kwargs": kwargs
            }
            continue
        if opt.get('dryrun', 0) == 1:
            continue
        resources[k]['driver'] = res['method'](**opt, driver_cfg=res['cfg'])


def main():
    cfg_file = f'{os.path.join(os.environ.get("TPSUP"), "python3", "scripts", "tpslnm_test_cfg.py")}'
    our_cfg = parse_cfg(cfg_file)

    print(f"after exec, our_cfg = {pformat(our_cfg)}{os.linesep}")
    # print(f"locals = {pformat(locals())}{os.linesep}")

    dict_cfg = parse_dict_cfg(our_cfg)
    print(f"dict_cfg = {pformat(dict_cfg)}{os.linesep}")

    input = "s=PERL lines='test line'"
    known = parse_input(input, dict_cfg)
    print(f'after parsed input="{input}"')
    print(f'known = {pformat(known)}{os.linesep}')

    run_batch(dict_cfg, [input], verbose=1, host_port='192.168.1.179:9333')


if __name__ == '__main__':
    main()
