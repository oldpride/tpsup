
from pprint import pformat
import re
import sys
import types
from typing import Union

from tpsup.cfgtools import check_syntax
from tpsup.cmdtools import run_cmd
from tpsup.exectools import eval_block, exec_into_globals
import tpsup.envtools
from tpsup.utiltools import resolve_scalar_var_in_string


swagger_syntax = {
    '^/$': {
        'cfg': {'type': dict, 'required': 1},
        'package': {'type': str},
        'minimal_args': {'type': str},
        'extra_args': {'type': dict},
    },

    # non-greedy match
    # note: don't use ^/cfg/(.+?)/$, because it will match /cfg/abc/def/ghi/, not only /cfg/abc/
    '^/cfg/([^/]+?)/$': {
        'base_urls': {'type': list, 'required': 1},
        'op': {'type': dict, 'required': 1},
        'entry':  {'type': [str, types.CodeType, types.FunctionType]},
    },
    '^/cfg/([^/]+?)/op/([^/]+?)/$': {
        'sub_url': {'type': str, 'required': 1},
        'num_args': {'type': int},
        'json': {'type': int},
        'method': {'type': str, 'pattern': r'^(GET|POST|DELETE)$'},
        'Accept': {'type': str},
        'comment': {'type': str},
        'validator': {'type': [str, types.CodeType, types.FunctionType]},
        'post_data': {'type': str},
        'test_str': {'type': list},
    },
}


def tpbatch_parse_hash_cfg(hash_cfg: dict, nojson=False, **opt):
    verbose = opt.get('verbose', 0)

    if verbose:
        print(f"hash_cfg = {pformat(hash_cfg)}")
        print(f"swagger_syntax = {pformat(swagger_syntax)}")

    check_syntax(hash_cfg, swagger_syntax, fatal=1,
                 skip_keys=["^imported.*",
                            "^module$",
                            "^meta$",
                            ],
                 verbose=verbose,
                 )

    if not hash_cfg.get('usage_example', None):
        example = "\n"

        for base in sorted(hash_cfg['cfg'].keys()):
            base_cfg = hash_cfg['cfg'][base]

            for op in sorted(base_cfg['op'].keys()):
                cfg = base_cfg['op'][op]
                example += f"   {{{{prog}}}} {base} {op}"

                num_args = cfg.get('num_args', 0)
                for i in range(num_args):
                    example += f" arg{i}"

                example += "\n"

                if cfg.get('comment') is not None:
                    example += f"      {cfg['comment']}\n"

                Accept = cfg.get('Accept', 'application/json')

                if ('json' in Accept or cfg.get('json')) and not nojson:
                    example += "      expect json in output\n"
                else:
                    example += "      not expect json in output\n"

                if cfg.get('validator'):
                    example += f"      validator: {cfg['validator']}\n"

                if cfg.get('test_str'):
                    for test_str in cfg['test_str']:
                        # when escape {{var}} in f"", double them up
                        example += f"      e.g. {{{{prog}}}} {base} {op} {test_str}\n"

                sub_url = cfg['sub_url']

                sub_ui = cfg.get('sub_ui')
                if sub_ui:
                    sub_ui = cfg['sub_ui']
                else:
                    sub_ui, discarded = sub_url.split('/', 1)
                    sub_ui += "/swagger-ui"

                for base_url in base_cfg['base_urls']:
                    example += f"        curl: {base_url}/{sub_url}\n"

                for base_url in base_cfg['base_urls']:
                    example += f"      manual: {base_url}/{sub_ui}\n"

                example += "\n"

        hash_cfg['usage_example'] = example

        hash_cfg['usage_top'] = f'''
    {{{{prog}}}} base operation arg1 arg2

    -nojson        don't apply json parser on output 
    -n | -dryrun   dryrun. only print out command.
    -v                                                              
        '''
    return hash_cfg


def tpbatch_parse_input(input, all_cfg, **opt):
    global known

    # this overrides the default tpsup.batch parse_input_default_way

    # command line like: tpswagger_test  mybase2 myop2_1 arg0 arg1
    #                                    base    op      args ...
    copied = input.copy()
    base = copied.pop(0)
    op = copied.pop(0)
    args = copied

    if base not in all_cfg['cfg']:
        print(f"ERROR: base='{base}' is not defined in cfg")
        exit(1)

    if op not in all_cfg['cfg'][base]['op']:
        print(f"ERROR: op='{op}' is not defined in cfg in base={base}")
        exit(1)

    num_args = all_cfg['cfg'][base]['op'][op].get('num_args', 0)

    num_input = len(copied)

    if num_args != num_input:
        print(f"ERROR: wrong number of args, expecting {num_args} but got {num_input}, input={copied}")
        exit(1)

    known = {'base': base, 'op': op, 'args': args}

    return known


def tpbatch_code(all_cfg, known, **opt):
    # this provides a default code() for tpsup.batch's config. see tpswagger_test_batch.cfg
    # can be overriden by a code() subroutine in cfg file.

    verbose = opt.get('verbose', 0)

    if verbose:
        print(f"all_cfg = {pformat(all_cfg)}")
        print(f"known   = {pformat(known)}")
        print(f"opt     = {pformat(opt)}")

    base = known['base']
    op = known['op']

    cfg = all_cfg['cfg'][base]['op'][op]

    if cfg is None:
        raise RuntimeError(f"base={base}, op={op}, doesn't exist")

    # push down upper level config to lower level
    upper_keys = ['base_urls', 'entry']
    cfg.update({k: all_cfg['cfg'][base][k] for k in upper_keys})
    cfg['op'] = op
    cfg['meta'] = all_cfg['meta']

    if verbose:
        print(f"base={base}, op={op}, cfg = {pformat(cfg)}")

    import tpsup.swaggertools
    tpsup.swaggertools.swagger(cfg, known['args'], **opt)


parsed_entry_decide_file = {}


def parse_login_by_method_pattern_file(pattern_file, **opt):
    if pattern_file not in parsed_entry_decide_file:
        ref = {}

        with open(pattern_file, 'r') as fh:
            for line in fh:
                if line.strip().startswith('#'):
                    continue
                if line.strip() == '':
                    continue

                line = line.strip()
                # print(f"line={line}")
                login, method, pattern = line.split(',', 3)
                # ref[method][login] = pattern
                ref.setdefault(method, {})
                ref[method][login] = pattern

        parsed_entry_decide_file[pattern_file] = ref

        if opt.get('verbose', 0):
            print(f"parsed {pattern_file} = {pformat(ref)}")

    return parsed_entry_decide_file[pattern_file]


def get_entry_by_method_suburl(cfg: dict, kvp: dict, **opt):
    # print "cfg=", Data::Dumper->Dump([$cfg], ['cfg']), "\n";
    # print "dict=", Data::Dumper->Dump([$dict], ['dict']), "\n";

    entry_decide_file = cfg.get('entry_decide_file', None)
    if not entry_decide_file:
        entry_decide_file = cfg['meta']['cfg_abs_path']
        entry_decide_file = entry_decide_file.replace('_cfg_batch.py', '_pattern.cfg')

    pattern_file = entry_decide_file
    #    print "pattern_file=$pattern_file\n";
    pattern_cfg = parse_login_by_method_pattern_file(pattern_file, **opt)
    #    print "pattern_by_login=", Data::Dumper::Dumper($pattern_by_login), "\n";

    method = cfg.get('method', 'GET')

    if method not in pattern_cfg:
        raise RuntimeError(f"cannot find method {method} in {pattern_file}")

    for login in pattern_cfg[method]:
        pattern = pattern_cfg[method][login]
        # print "login=$login, pattern=$pattern, sub_url=$cfg->{sub_url}\n";

        # check if sub_url with or without leading /
        if re.search(pattern, cfg['sub_url']) or re.search(pattern, f"/{cfg['sub_url']}"):
            return login

    raise RuntimeError(f"cannot find login for method={method}, sub_url={cfg['sub_url']} in {pattern_file}")


def swagger(cfg, args,
            dryrun=0,
            nojson=0,
            **opt):
    verbose = opt.get('verbose', 0)

    if verbose:
        print(f"cfg = {pformat(cfg)}")
        print(f"args = {pformat(args)}")
        print(f"opt = {pformat(opt)}")

    kvp = {}

    if args:
        verbose and print(f"args = {args}")

        n = len(args)

        for i in range(n):
            kvp[f"A{i}"] = args[i]

    validator = cfg.get('validator')
    if validator is not None:
        verbose and print(f"test validator: {validator}")

        if type(validator) is str:
            # it is a scalar
            validator = resolve_scalar_var_in_string(validator, kvp, **opt)
            if eval_block(validator, EvalAddReturn=1, **opt):
                verbose and print("validator test passed")
            else:
                print(f"validator test failed: {validator}")
                exit(1)
        else:
            if validator(args, cfg, opt):
                verbose and print("validator test passed")
            else:
                print(f"validator test failed: {validator}")
                exit(1)

    # sub_url = cfg['sub_url']
    sub_url = resolve_scalar_var_in_string(cfg['sub_url'], kvp, **opt)

    base_urls = cfg['base_urls']

    for base_url in base_urls:
        flags = []
        if verbose:
            print(f"resolved url = {base_url}/{sub_url}")
            flags.append('-v')
        else:
            flags.append('--silent')

        flag_string = ' '.join(flags)

        method = cfg.get('method', 'GET')
        Accept = cfg.get('Accept', 'application/json')

        entry = cfg.get('entry')
        entry_type = type(entry)

        verbose and print(f"entry = {entry}, entry_type = {entry_type}")

        if entry_type is str:
            entry_name = entry
        else:
            entry_name = entry(cfg, kvp, **opt)

        # curl = '/usr/bin/curl'
        # myenv = tpsup.envtools.Env()
        # if myenv.isWindows():
        #     curl = "C:\\Windows\\System32\\curl.exe"
        curl = "curl"

        command = f'{flag_string} -w "http_code: %{{http_code}}" -X {method} --header "Accept: {Accept}"'

        if entry_name:
            command = f"ptentry -- {curl} -u tpentry{entry_name}user:tpentry{entry_name}decoded {command}"
        else:
            command = f"{curl} {command}"

        if method == 'POST':
            post_data = cfg.get('post_data')

            if post_data is not None:
                # sometimes curl's POST method doesn't want -d at all.
                # therefore don't use -d '' when it is not defined.
                post_data = post_data.format(**kvp)
                command += f" --header 'Content-Type: application/json' -d '{post_data}'"

        command += f" {base_url}/{sub_url}"

        if dryrun:
            print(f"DRYRUN: {command}")
        else:
            print(f"command = {command}")
            # system($command);
            result = run_cmd(command)
            rc = result['rc']
            if rc:
                print(result['stdout'])
                print(result['stderr'], file=sys.stderr)
                print(f"ERROR: command failed: rc={rc}", file=sys.stderr)
                exit(1)
            else:
                lines = result['stdout'].splitlines()
                status_line = lines.pop()

                if Accept.find('json') >= 0 and cfg.get('json') and not nojson:
                    # 'Accept' is from caller of cfg
                    # 'json' is from cfg
                    # 'nojson' is from caller - likely from command line
                    json_cmd = "python -m json.tool"
                    result = run_cmd(f"echo '{lines}' | {json_cmd}")
                    print(result['stdout'])
                    print(status_line)
                else:
                    print('\n'.join(lines))
                    print(status_line)


tpbatch = {
    # will be called by tpsup.batch
    'parse_hash_cfg': tpbatch_parse_hash_cfg,
    'parse_input_sub': tpbatch_parse_input,
    'code': tpbatch_code,
}


def main():
    # we don't export anything because this module is called by TPSUP::BATCH.
    print("------------ test swagger -----------------------------\n")


if __name__ == '__main__':
    main()
