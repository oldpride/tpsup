import inspect
import os
import re
from pprint import pformat
from time import localtime, strptime
from typing import Dict, List, Union, Callable

import tpsup.util
import tpsup.cmdtools
import tpsup.exectools

# converted  from ../../../lib/perl/TPSUP/TRACER.pm


def parse_input(input: Union[list, str], **opt):
    if isinstance(input, str):
        input = input.split()

    if not isinstance(input, list):
        raise Exception(
            f'input must be a list or a string, but it is {type(input)}')

    pair_pattern = re.compile(r'(\w+)=(.*)')

    ref = {}

    for pair in input:
        if re.match(r'any|check', re.IGNORECASE):
            return
        elif pair_pattern.match(pair):
            key, value = pair_pattern.match(pair).groups()
            # convert key to upper case so that user can use both upper case and lower case
            # on command line.
            key = key.upper()

            # if qty, remove comma
            if "QTY" in key:
                value = value.replace(',', '')

            ref[key] = value
        else:
            raise Exception(
                f'input must be a list of key=value pairs, but {pair} is not')

    if AliasMap := opt.get('AliasMap', None):
        for alias in AliasMap.keys():
            key = AliasMap[alias]

            uc_alias = alias.upper()
            if uc_alias in ref:
                ref[key] = ref[uc_alias]  # remember key is already upper case

    check_allowed_keys(ref, **opt)

    return ref


def check_allowed_keys(ref: dict, **opt):
    if not (allowed_keys := opt.get('AllowedKeys', None)):
        return

    # check ref is empty
    if not ref:
        return

    allowed = {}
    for key in allowed_keys:
        allowed[key.upper()] = True

    if allowed_keys:
        for key in ref.keys():
            if key not in allowed_keys:
                raise Exception(f'key {key} is not allowed')
    return


def get_keys_in_uppercase(cfg_by_entity: dict, **opt):
    print(f"opt = {pformat(opt)}")

    seen = {}

    for entity in cfg_by_entity.keys():
        wc = cfg_by_entity[entity].get(
            'method_cfg', {}).get('where_clause', {})
        for k in wc.keys():
            seen[k.upper()] = 1

    for k in opt.get("ExtraKeys", []):
        seen[k.upper()] = 1

    for a, k in opt.get("AliasMap", {}).items():
        uc_k = k.upper()
        if not uc_k in seen:
            raise RuntimeError(
                f"{k} is used in AliasMap but {k} is not seen in original keys: {pformat(seen)}")

        seen[a.upper()] = 1

    for k in opt.get("key_pattern", {}).keys():
        seen[k.upper()] = 1

    return seen.keys()


def __line__():
    return __line__
    return inspect.currentframe().f_back.f_lineno


def __file__():
    return __file__


def resolve_a_clause(clause: str, dict1: dict, **opt):
    # in python, both dict and Dict are reserved words.
    # therefore, we use dict1 instead of dict or Dict.

    # first substitute the scalar var in {{...}}
    opt['verbose'] and print(
        f"line {__line__()} before substitution, clause = {clause}, dict1 = {pformat(dict1)}")

    clause = tpsup.util.resolve_scalar_var_in_string(clause, dict1, **opt)

    opt['verbose'] and print(
        f"line {__line__()} after substitution, clause = {clause}")

    # we don't need this because we used 'our' to declare %known.
    # had we used 'my', we would have needed this.
    # my $touch_to_activate = \%known;

    # then eval() other vars, eg, $known{YYYYMMDD}
    clause2 = tracer_eval_code(clause, dict1=dict1, **opt)

    return clause2


def resolve_vars_array(vars: list, dict1: dict, **opt):
    if not vars:
        return {}

    # vars is a ref to array.
    if not isinstance(vars, list):
        raise Exception(f"vars type is not list. vars = {vars}")

    ref = {}

    # copy to avoid modifying original data
    dict2 = {}
    dict2.update(dict1)
    vars2 = vars.copy()

    while vars2:
        k = vars2.pop(0)
        v = vars2.pop(0)

        v2 = resolve_a_clause(v, dict2, **opt)

        ref[k] = v2
        dict2[k] = v2  # previous variables will be used to resolve later variables

    return ref


def cmd_output_string(cmd: str, **opt):
    string = tpsup.cmdtools.run_cmd_clean(cmd, **opt)
    return string


def process_code(entity: str, method_cfg: dict, vars: dict, **opt):
    # all handling have been done by caller, process_entity
    return


method_syntax = {
    'code': {
        'required': [],
        'optional': [],
    },
    'db': {
        'required': ['db', 'db_type'],
        'optional': ['table', 'template', 'where_clause', 'order_clause', 'example_clause', 'extra_clause', 'header'],
    },
    'cmd': {
        'required': ['type', 'value'],
        'optional': ['example', 'file', 'grep', 'logic', 'MatchPattern', 'ExcludePattern', 'extract'],
    },
    'log': {
        'required': ['log', 'extract'],
        'optional': ['MatchPattern', 'ExcludePattern'],
    },
    'section': {
        'required': ['log', 'ExtractPatterns'],
        'optional': ['PreMatch', 'PreExclude', 'PostMatch', 'PostExclude', 'BeginPattern', 'EndPattern', 'KeyAttr', 'KeyDefault'],
    },
    'path': {
        'required': ['paths'],
        'optional': ['RecursiveMax', 'HandleExp'],
    },

}


attr_syntax = {
    'tests': {
        'required': ['test'],
        'optional': ['if_success', 'if_failed', 'condition'],
    },
}

entity_syntax = {
    'required': ['method'],
    'optional': ['method_cfg', 'AllowZero', 'AllowMultiple', 'comment', 'top', 'tail', 'update_key',
                 'code', 'pre_code', 'post_code', 'vars', 'condition', 'tests', 'csv_filter',

                 'MaxColumnWidth', 'output_key'],
}


###### global variables - begin ######
known = {}  # knowledge
vars = {}  # entity-level vars
row_count = None  # from cmd, db, log extract,
# whereever @lines/@arrays/@hashes is used.
lines = []  # from cmd output, array of strings
output = None  # from cmd output
rc = None  # from cmd output
arrays = []  # from db  output, array of arrays
headers = []  # from db  output, array
hashes = []  # from db/log extraction and section, array of hashes
hash1 = {}  # converted from @hashes using $entity_cfg->{output_key}
r = {}  # only used by update_knowledge_from_row
###### global variables - end ######

cfg_by_file = {}


def parse_cfg(cfg_file: str, **opt):
    verbose = opt.get('verbose', 0)

    if cfg_file in cfg_by_file:
        return cfg_by_file[cfg_file]

    if not os.path.isfile(cfg_file):
        raise RuntimeError(f"{cfg_file} not found")
    if not os.access(cfg_file, os.R_OK):
        raise RuntimeError(f"{cfg_file} not readable")

    cfg_abs_path = os.path.abspath(cfg_file)
    cfgdir, cfgname = os.path.split(cfg_abs_path)  # dirname and basename

    with open(cfg_file) as fh:
        cfg_string = fh.read()

    global our_cfg
    # exec will set our_cfg
    exec_simple(cfg_string, source_filename=cfg_file)

    # make data structure consistent
    for k in ['trace_route']:
        if k in our_cfg:
            our_cfg[k] = tpsup.util.unify_array_hash(our_cfg[k], 'entity')

    # 'vars' is array of pairs of key=>value
    # 'value' is an expression, therefore, we need to use two different quotes.
    # unshift put the key=value to the front, therefore, allow cfg file to overwrite it.
    our_cfg['vars'].insert(0, ('cfgdir', f"'{cfgdir}'"))
    our_cfg['vars'].insert(0, ('cfgname', f"'{cfgname}'"))

    if 'key_pattern' in our_cfg:
        our_cfg['key_pattern'] = tpsup.util.unify_hash_hash(
            our_cfg['key_pattern'], 'pattern')
    else:
        our_cfg['key_pattern'] = {}

    cfg_by_entity = our_cfg.get('cfg_by_entity', None)
    alias_map = our_cfg.get('alias_map', {})
    extra_keys = our_cfg.get('extra_keys', [])
    entry_points = our_cfg.get('entry_points', [])
    trace_route = our_cfg.get('trace_route', [])
    extend_key_map = our_cfg.get('extend_key_map', [])

    # checking for required attributes
    if not cfg_by_entity:
        raise RuntimeError(f"missing cfg_by_entity in {cfg_file}")

    entities = sorted(cfg_by_entity.keys())
    required_attr = ['method']

    failed = 0
    for e in entities:
        entity_cfg = cfg_by_entity[e]

        if not isinstance(entity_cfg, dict):
            raise RuntimeError(
                f"entity={e}, cfg has wrong type='{type(entity_cfg)}'. {pformat(entity_cfg)}")

        if not check_cfg_keys(entity_cfg, entity_syntax, **opt):
            print(f"ERROR: entity={e}, entity_cfg check failed\n\n")
            failed += 1

        method = entity_cfg['method']
        method_cfg = entity_cfg.get('method_cfg', None)

        if method == 'code':
            if method_cfg:
                print(
                    f"entity={e} is method={method} which should not have method_cfg\n")
                failed += 1
                continue
        else:
            if not method_cfg:
                print(
                    f"entity={e} is method={method} which should have method_cfg\n")
                failed += 1
                continue

        if not method_syntax.get(method, None):
            print(
                f"method={method} in entity={e} but not in defined method_syntax\n")
            failed += 1

        if method_cfg:
            if not check_cfg_keys(method_cfg, method_syntax[method], **opt):
                print(f"ERROR: entity={e}, method_cfg check failed\n")
                failed += 1

            tests = entity_cfg.get('tests', [])
            for test in tests:
                if not check_cfg_keys(test, attr_syntax['tests'], **opt):
                    print(
                        f"ERROR: a test in entity={e} attr=tests check failed\n")
                    failed += 1

    if failed:
        raise RuntimeError(f"found at least {failed} errors.")

    allowed_keys = get_keys_in_uppercase(cfg_by_entity,
                                         AliasMap=alias_map,
                                         ExtraKeys=extra_keys,
                                         key_pattern=our_cfg['key_pattern'],
                                         )

    trace_route_entities = tpsup.util.get_keys_from_array(
        trace_route, 'entity')

    for e in trace_route_entities:
        if e not in cfg_by_entity:
            raise RuntimeError(
                f"entity '{e}' in trace_route is not defined. file={cfg_file}.\n")

    usage_detail = f"""
    keys: {allowed_keys}

    entities are: {entities}

    keys and entities are case-insensitive

    trace route: {trace_route_entities}
    """

    if 'YYYYMMDD' in allowed_keys:
        today = strptime("%Y%m%d", localtime())
        usage_detail += f"\n   yyyymmdd is default to today {today}\n"

    extender_by_key = {}  # this provides the quick access to the extender function
    extender_keys = []    # this provides the order of the map
    if extend_key_map:
        for row in extend_key_map:
            k, func = row

            extender_keys.append(k)

            extender_by_key[k] = func

        # add this into entity cfg so that later we only need to pass entity cfg
        for e in entities:
            cfg_by_entity[e]['extender_by_key'] = extender_by_key

    our_cfg.update({
        'allowed_keys': allowed_keys,
        'entities': entities,
        'trace_route_entities': trace_route_entities,
        'extender_keys': extender_keys,
        'extender_by_key': extender_by_key,
        'usage_detail': usage_detail,
    })

    for e in entities:
        # push down some higher-level config because we may pass the lower config only
        entity_cfg = cfg_by_entity[e]

        entity_cfg['entity'] = e

    cfg_by_file[cfg_file] = our_cfg

    # check syntax
    BeginCode = "global known, our_cfg, row_count, rc, output, lines, arrays, hashes, hash1, r\n"
    node_pairs = tpsup.util.get_node_list(our_cfg, 'our_cfg', **opt)
    # vars is a array in pairs, therefore, we need to check odd-numberred elements
    # tvars= ['k1', 'v1', 'k2', 'v2']
    # get_node_list(test_object, '/root') =
    # ['/root/[0]', 'k1',
    #  '/root/[1]', 'v1',
    #  '/root/[2]', 'k2',
    #  '/root/[3]', 'v2']
    eval_patterns = [
        # vars are pairs. odd-numberred are values.
        re.compile(r'\{vars\}/\[\d*[13579]\]$'),

        # these are all hash keys
        re.compile(
            r'\{(condition|code|pre_code|post_code|test|if_fail|if_success|update_knowledge|Exps)\}$'),
    ]

    temporary_replacement_pattern = re.compile(r'\{\{([0-9a-zA-Z_.-]+)\}\}')

    failed = 0  # restart count

    while node_pairs:
        node = node_pairs.pop(0)
        value = node_pairs.pop(0)

        for p in eval_patterns:
            if p.search(node):
                verbose > 1 and print(f"matched {node}")
                clause = value

                # replace all scalar vars {{...}} with 1,
                # but exclude {{pattern::...} and {{where::...}}
                clause = temporary_replacement_pattern.sub(
                    '1', clause, flags=re.MULTILINE)

                if not tpsup.exectools.exec_into_globals(clause,
                                                         globals(), locals(),
                                                         compile_only=1,
                                                         BeginCode=BeginCode,
                                                         verbose=(verbose > 1)):
                    failed = 1
                    print(f"ERROR: failed to compile node: {node}\n")
                    print(
                        "In order to test compilation,"
                        "we temporarily substituted vars in {{}} with '1'\n")

    if failed:
        raise RuntimeError("some python code failed to compile")

    return our_cfg


def exec_simple(source: str, **opt):
    tpsup.exectools.exec_into_globals(source, globals(), locals(), **opt)


def check_cfg_keys(cfg: dict, syntax: dict, **opt):
    verbose = opt.get('verbose', 0)

    if not cfg:
        print(f"ERROR: cfg={cfg}, not populated")
        return 0

    failed = 0
    for a in syntax['required']:
        if not a in cfg:
            print(f"missing required attr='{a}' in cfg")
            failed += 1

    allowed_attr = {}
    for a in syntax['required'] + syntax['optional']:
        allowed_attr[a] = 1

    for a in cfg.keys():
        if not a in allowed_attr:
            print(f"ERROR: attr='{a}' is not allowed in cfg")
            failed += 1

    if failed:
        print(f"ERROR: found at least {failed} errors.")
        verbose and print(f"cfg = {pformat(cfg)}")
        verbose and print(f"syntax = {pformat(syntax)}")
        return 0

    return 1


def tracer_eval_code(code: str, **opt):
    verbose = opt.get('verbose', 0)

    global vars
    global known

    # this relies on global buffer that are specific to TPSUP::TRACER
    # default dictionary is vars, known
    dict1 = opt.get('dict1', {**vars, **known})

    if verbose:
        print(f"------ begin preparing code ------")
        print(f"original code: {code}")

    code = tpsup.util.resolve_scalar_var_in_string(code, dict1, **opt)

    if verbose:
        print(f"afer substituted scalar vars in '{{...}}': {code}")

    ret = tpsup.exectools.eval_block(code, globals(), locals(), **opt)

    return ret


def main():
    global known

    known = {
        'a': 1,
        'b': 'hello'
    }

    tests = [
        ('''
        # simple statements, no return
        a={{a}}
        b='{{b}}'
        print(f"a={a}")
        print(f"b={b}")
        ''',
         0  # verbose
         ),
        (
            '''
        # with return
        a={{a}}
        b='{{b}}'
        print(f"a={a}")
        print(f"b={b}")
        b.startswith('h')
        ''',
            0  # verbose
        )
    ]
    for code, verbose in tests:
        print()
        print('----------------------------------------')
        print(f"code = {code}")
        ret = tracer_eval_code(code, **{'verbose': verbose})
        print(f"ret = {ret}")

    print()
    print('----------------------------------------')
    import os
    TPSUP = os.environ.get('TPSUP')
    cfg_file = f'{TPSUP}/python3/lib/tpsup/tracer_test_cfg.py'
    print(f'parse_cfg(cfg_file) = {pformat(parse_cfg(cfg_file))}')


if __name__ == '__main__':
    main()
