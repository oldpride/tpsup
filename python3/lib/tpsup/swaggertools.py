
from pprint import pformat
import types
from typing import Union

from tpsup.cfgtools import check_syntax


swagger_syntax = {
    'top': {
        'cfg': {'type': dict, 'required': 1},
        'package': {'type': str},
        'minimal_args': {'type': str},
    },

    'base': {
        'base_urls': {'type': list, 'required': 1},
        'op': {'type': dict, 'required': 1},
        'entry': {'type': str},
        'entry_func': {'type': Union[str, types.CodeType, types.FunctionType]},
    },
    'op': {
        'sub_url': {'type': str, 'required': 1},
        'num_args': {'type': str, 'pattern': r'^\d+$'},
        'json': {'type': str, 'pattern': r'^\d+$'},
        'method': {'type': str, 'pattern': r'^(GET|POST|DELETE)$'},
        'Accept': {'type': str},
        'comment': {'type': str},
        'validator': {'type': [str, types.CodeType, types.FunctionType]},
        'post_data': {'type': str},
        'test_str': {'type': list},
    },
}


def tpbatch_parse_hash_cfg(hash_cfg: dict, **opt):
    verbose = opt.get('verbose', 0)

    if verbose:
        print(f"hash_cfg = {pformat(hash_cfg)}")
        print(f"swagger_syntax = {pformat(swagger_syntax)}")

    check_syntax(hash_cfg, swagger_syntax, fatal=1)

    if not hash_cfg.get('usage_example'):
        example = "\n"

        for base in sorted(hash_cfg['cfg'].keys()):
            base_cfg = hash_cfg['cfg'][base]

            for op in sorted(base_cfg['op'].keys()):
                cfg = base_cfg['op'][op]
                example += f"   {{prog}} {base} {op}"

                num_args = cfg.get('num_args', 0)
                for i in range(num_args):
                    example += f" arg{i}"

                example += "\n"

                if cfg.get('comment') is not None:
                    example += f"      {cfg['comment']}\n"

                Accept = cfg.get('Accept', 'application/json')

                if ('json' in Accept or cfg.get('json')) and not opt.get('nojson'):
                    example += "      expect json in output\n"
                else:
                    example += "      not expect json in output\n"

                if cfg.get('validator'):
                    example += f"      validator: {cfg['validator']}\n"

                if cfg.get('test_str'):
                    for test_str in cfg['test_str']:
                        example += f"      e.g. {{prog}} {base} {op} {test_str}\n"

                sub_url = cfg['sub_url']

                sub_ui = cfg.get('sub_ui')
                if sub_ui:
                    sub_ui = cfg['sub_ui']
                else:
                    sub_ui, discarded = sub_url.split('/')
                    sub_ui += "/swagger-ui"

                for base_url in base_cfg['base_urls']:
                    example += f"        curl: {base_url}/{sub_url}\n"

                for base_url in base_cfg['base_urls']:
                    example += f"      manual: {base_url}/{sub_ui}\n"

                example += "\n"

        hash_cfg['usage_example'] = example

        hash_cfg['usage_top'] = f'''
    {{prog}} base operation arg1 arg2

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
    upper_keys = ['base_urls', 'entry', 'entry_func']
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
                login, method, pattern = line.split(',', 2)
                ref[method][login] = pattern

        parsed_entry_decide_file[pattern_file] = ref

    return parsed_entry_decide_file[pattern_file]


def get_entry_by_method_suburl(cfg: dict, kv_dict, **opt):
    # print "cfg=", Data::Dumper->Dump([$cfg], ['cfg']), "\n";
    # print "dict=", Data::Dumper->Dump([$dict], ['dict']), "\n";

    entry_decide_file = cfg.get('entry_decide_file', None)
    if entry_decide_file:
        entry_decide_file = cfg['entry_decide_file']
    else:
        entry_decide_file = cfg['meta']['cfg_abs_path']
        entry_decide_file = entry_decide_file.replace('_batch.cfg', '_pattern.cfg')

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

        if cfg['sub_url'] in pattern or f"/{cfg['sub_url']}" in pattern:
            return login

    raise RuntimeError(f"cannot find login for method={method}, sub_url={cfg['sub_url']} in {pattern_file}")


def main():
    # we don't export anything because this module is called by TPSUP::BATCH.
    print("------------ test swagger -----------------------------\n")


if __name__ == '__main__':
    main()
