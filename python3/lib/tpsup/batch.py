# 4 major fles
#    batch.py
#    tpbatch.py
#    app_module.py # this is optional
#    app_cfg.py
#
# flow:
#    tpbatch.py calls batch.py
#    batch.py loads and parses app_cfg.py
#    app_cfg.py will use app_module.py.
#
# batch.py is the main namespace. globals() is batch.py.
#

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


def exec_simple(source, **opt):
    return exec_into_globals(source, globals(), locals(), **opt)


# extra_args is a dict of dict instead of a list of dict,
# this allows override later by key, which is 'dest' in argparse.
# argparse takes a list of dict but it doesn't allow same
# 'dest' to be used twice.
# we use 'dest' as the key to override. later convert dict to list.
extra_args = {
    'caller': {'switches': ['-c', '--caller'], 'action': 'store', 'default': None, 'help': "caller name"},

    'dryrun': {'switches': ['-dryrun', '--dryrun'], 'action': 'store_true', 'default': False,
               'help': "dryrun mode if implemented"},

    'debug': {'switches': ['-debug', '--debug'], 'action': 'store_true', 'default': False, 'help': "debug mode"},

    'interactive': {'switches': ['--interactive'], 'action': 'store_true', 'default': False,
                    'help': "interactive mode if implemented"},

    'no_post_batch': {'switches': ['-np', '--no_post_batch'], 'action': 'store_true', 'default': False,
                      'help': "not to run post_batch"},

    'batch': {'switches': ['-b', '--batch'], 'action': 'store', 'default': None,
              'help': "file has command args, one line per call. if file is '-', it means STDIN"},

    'record': {'switches': ['--record'],
               'action': 'store',
               'help': 'record keys (separated by comma) to avoid run twice'},

    'record_file': {'switches': ['--record_file'],
                    'default': None,
                    'action': 'store',
                    'help': f'record to this file, default to under {tpsup.tptmp.get_dailydir()}'},

    'retry': {'switches': ['--retry'], 'action': 'store', 'default': 0, 'type': int, 'help': "retry times"},

    'retry_reset': {'switches': ['--retry_reset'], 'default': 1, 'type': int,
                    'action': 'store',
                    'help': 'reset driver before retry input, ie, run post_batch and pre_batch, default 1'},
}

# global vars needed for exec()
# our_cfg = None


def parse_cfg(cfg_file: str = None, **opt):
    verbose = opt.get('verbose', 0)

    # global vars needed for exec()
    global our_cfg

    with open(cfg_file, 'r') as f:
        source = f.read()

    exec_simple(source, source_filename=cfg_file)

    if verbose:
        print(f'after exec, our_cfg = {pformat(our_cfg)}')

    # our_cfg = asdict(mod.our_cfg)

    imported_tpbatch = {}
    if module := our_cfg.get('module', None):
        if not type(module) is str:
            raise Exception(
                f"module must be a string, but it is {type(module)}")
        imported = importlib.import_module(module)
        our_cfg['imported'] = imported

        if hasattr(imported, 'tpbatch'):
            imported_tpbatch = imported.tpbatch
            our_cfg['imported_tpbatch'] = imported_tpbatch

    if parse_dict_cfg_sub := imported_tpbatch.get('parse_dict_cfg'):
        pass
    else:
        # default is defined int this file
        parse_dict_cfg_sub = parse_dict_cfg

    our_cfg = parse_dict_cfg_sub(our_cfg, **opt)

    # unify all configs under our_cfg (later becomes all_cfg),
    # make it include functions of app_cfg.py (pre_batch, post_batch, ...).
    # this makes easier to access.
    #
    # config precedence:
    #     1. cfg file - eg, pyslnm_test_input_cfg.py, which is loaded into a our_cfg dict.
    #     2. module - eg, seleniumtools.py - which is loaded into our_cfg['imported_tpbatch'].
    #     3. this file - batch.py - which is globals().
    # try to consolidate all the overrides logic here.
    #
    # there is actually a higher override precedence: command line.
    #     - It is done in tpbatch.py.
    #     - It is not in this file because parse_cfg() needs to be called (to
    #       get all_cfg's extra_args) before parsing command line.

    # globals() vs our_cfg (later becomes all_cfg).
    #    globals() is the current module namespace.
    #       it has all classes, functions, variables, ...
    #    our_cfg (all_cfg) is one variable in globals().
    #        it is a dict in app_cfg.py,
    #        without functions of app_cfg.py.
    # because pre_batch is a function, it is not in all_cfg.
    # therefore, the following code will not work:
    #    pre_batch = all_cfg.get("pre_batch", None)

    # dicts to be merged from 3 places: cfg file, module, this file.
    for k in [
        'extra_args',  # can be in 3 places: cfg file, module, this file.
        'resources',  # can be in 2 places: cfg file, module
    ]:
        our_cfg[k] = {
            **globals().get(k, {}),
            **imported_tpbatch.get(k, {}),
            **our_cfg.get(k, {}),
        }

    # ways to check function existence
    #   1st method to check function existence
    #     if not (parse_input_sub := globals().get("parse_input_sub", None)):  # check function existence
    #         parse_input_sub = parse_input_default_way
    #
    #   2nd method to check function existence
    #     global parse_input_sub
    #     try:
    #         parse_input_sub
    #     except NameError:
    #         parse_input_sub = parse_input_default_way

    # values or functions from 3 places: cfg file, module, this file.
    default_by_key = {
        'parse_input_sub': parse_input_default_way,
        'parse_dict_cfg': parse_dict_cfg,  # this function is only used in this funciton
    }

    for f in [
        'pre_batch',  # can be in 2 places: cfg file, module
        'post_batch',  # can be in 2 places: cfg file, module
        'code',  # can be in 2 places: cfg file, module
        'parse_input_sub',  # can be in 3 places: cfg file, module, this file.
        'parse_dict_cfg',  # can be in 3 places: cfg file, module, this file.
    ]:
        if f in globals():
            our_cfg[f] = globals()[f]
        elif f in imported_tpbatch:
            our_cfg[f] = imported_tpbatch[f]
        else:
            our_cfg[f] = default_by_key.get(f, None)

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
    parse_input_sub = all_cfg["parse_input_sub"]
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

    verbose = opt.get('verbose', 0)

    parsed_batch = []
    if verbose:
        print(f"parse_batch: type(batch)={type(batch)}")
    if type(batch) == str:
        filename = batch

        batch_cutoff = all_cfg.get('batch_cutoff', None)
        if batch_cutoff:
            # get batch file timestamp and compare with today
            batch_mtime = os.path.getmtime(filename)
            batch_mtime_str = datetime.fromtimestamp(
                batch_mtime).strftime('%Y%m%d%H%M%S')
            if batch_cutoff == 'today':
                cutoff_str = datetime.today().strftime('%Y%m%d') + '000000'
            elif batch_cutoff.startswith('today-'):
                cutoff_str = datetime.today().strftime('%Y%m%d') + \
                    batch_cutoff[6:] + '0000'
            else:
                cutoff_str = batch_cutoff

            # string compare
            if batch_mtime_str < cutoff_str:
                print("")
                print(
                    f"{batch} timestamp={batch_mtime_str} is older than cutoff={cutoff_str}, skip !!!")
                print("")
                return []
            else:
                print(
                    f"{batch} timestamp={batch_mtime_str} is newer than cutoff={cutoff_str}, continue")

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
    elif verbose:
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
        print(file=sys.stderr)
        print(f'run_batch: given_cfg = {pformat(given_cfg)}', file=sys.stderr)
        print(file=sys.stderr)
        print(f'run_batch: batch = {pformat(batch)}', file=sys.stderr)
        print(file=sys.stderr)

    parsed_batch = parse_batch(given_cfg, batch, **opt)

    set_all_cfg(given_cfg, **opt)
    all_cfg = get_all_cfg(**opt)
    if verbose:
        print(f'run_batch: all_cfg = {pformat(all_cfg)}', file=sys.stderr)
        print(file=sys.stderr)

    cfg_opt = all_cfg.get('opt', {})
    if verbose:
        print(f'run_batch: cfg_opt = {pformat(cfg_opt)}', file=sys.stderr)
        print(file=sys.stderr)

    opt2 = {**cfg_opt, **opt}  # combine dicts/kwargs
    if verbose:
        print(f'run_batch: opt2 = {pformat(opt2)}', file=sys.stderr)
        print(file=sys.stderr)

    # record = all_cfg.get('record', None)
    # we retrieve record from opt2, because it may be overwritten by command line
    record = opt2.get('record', None)
    record_keys = []
    seen_record = {}
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
            script_name = os.path.basename(
                all_cfg.get('cfg_file', 'unknown.txt'))

            # dailydir = tpsup.tptmp.tptmp().get_dailydir()
            # record_file = f'{dailydir}/{script_name.replace(".py", ".log")}'
            record_file = tpsup.tptmp.tptmp().get_dailylog(prefix=script_name)
        print("record_file = ", record_file, file=sys.stderr)
        # check whether record_file exists
        if os.path.exists(record_file):
            with open(record_file, 'r') as ifh:
                whole_file = ifh.read()
                record_lines = whole_file.split('\n')
                for line in record_lines:
                    # split line at the first comma
                    # use optional args to avoid ValueError:
                    #      not enough values to unpack (expected at least 2, got 1)
                    timestamp, record_string, *_ = line.split(',', 1) + [None]
                    if record_string is None:
                        continue
                    seen_record[record_string] = timestamp
        record_ofh = open(record_file, 'a')

    init_resources(all_cfg, **opt2)

    if verbose > 1:
        print(f'all_cfg = {pformat(all_cfg)}', file=sys.stderr)
        print(f'opt2 = {pformat(opt2)}', file=sys.stderr)

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

    pre_batch = all_cfg.get("pre_batch", None)
    post_batch = all_cfg.get("post_batch", None)

    pre_batch_already_done = False
    # we delay pre_batch() till we really need to run the code()

    known = {}

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
                    f'already seen record at "{seen_record[record_string]},{record_string}". skipped.', file=sys.stderr)
                continue

        if pre_batch and not pre_batch_already_done:
            pre_batch_already_done = True

            pre_batch(all_cfg, known, **opt2)

        if code_sub := all_cfg.get("code", None):
            retry = int(opt2.get("retry", 0))
            if not retry:
                code_sub(all_cfg, known, **opt2)
            else:
                while True:
                    success = False
                    retry_reset = opt2.get("retry_reset", 1)
                    try:
                        code_sub(all_cfg, known, **opt2)
                        # todo: check return value
                        success = True
                    except Exception as e:
                        print(f'exception caught: {e}', file=sys.stderr)
                        if verbose:
                            traceback.print_exc()
                    if success:
                        break
                    else:
                        if retry > 0:
                            print(
                                f'task failed, but retry={retry}, so we retry', file=sys.stderr)
                            retry = retry - 1

                            if retry_reset:
                                if post_batch:
                                    post_batch(all_cfg, known, **opt2)
                                if pre_batch:
                                    pre_batch(all_cfg, known, **opt2)
                        else:
                            raise RuntimeError(
                                f'task failed after all retries. input={pformat(input)}')

        else:
            print(
                f'function code is not defined in cfg or driver module, therefore, not run', file=sys.stderr)

        if record:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            seen_record[record_string] = timestamp
            line = f"{timestamp},{record_string}"
            print(f"record: {line}", file=sys.stderr)
            record_ofh.write(f"{line}\n")
            # record_ofh.flush()

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

    if post_batch and not opt.get('no_post_batch', 0):
        post_batch(all_cfg, known, **opt2)

    return


def resolve_record_keys(keys, known):
    values = [known.get(k.upper(), '') for k in keys]  # upper case keys
    record_string = ','.join(values)
    return record_string


def init_resources(all_cfg: Dict, **opt):
    verbose = opt.get('verbose', 0)

    resources = all_cfg.get('resources', {})

    for k, res in resources.items():
        if res.get('enabled', 1) == 0:
            continue

        if not 'cfg' in res:
            res['cfg'] = {}

        # this is the way to copy **kwargs
        kwargs = {}
        kwargs['driver_cfg'] = res['cfg']
        kwargs.update(opt)  # let command line options override cfg options

        resources[k]['driver_call'] = {
            "method": res['method'],
            "kwargs": kwargs
        }

        if res.get('init_resource', 1) == 0:
            # if not initiate it now, we pass back function name and params, so that
            # caller can initiate it at another time
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
