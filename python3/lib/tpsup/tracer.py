import inspect
import os
import re
from pprint import pformat
from time import localtime, strftime, strptime
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
    # print(f"opt = {pformat(opt)}")

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


def update_knowledge_from_rows(row: dict, cfg: dict, **opt):
    if not row or not row.keys():
        return

    if not cfg:
        return

    r = row.copy()

    # $key_cfg is mapping between $known's keys and $rows' keys (column names), as they may
    # be different in spelling
    # $key_cfg = {
    #    known_key1 => 'row_key1',  # this converted to below after unify_hash() call.
    #    known_key1 => { column=>row_key1 },
    #    known_key2 => { column=>row_key2, flag2=>value },
    #    known_key3 => { flag3=>value },    # here we default column = known_key3
    #    known_key4 => {},                  # here we default column = known_key4
    #    ...
    # },

    for k, kc in cfg.items():
        kc_type = type(kc)
        if kc_type is str:
            kc = {'column': k}

        # condition = kc.get('condition', None) or kc.get('update_knowledge', None)
        condition = kc.get('condition', None)

        if condition:
            if not re.search(r'{{new_value}}', condition):
                # if condition doesn't need {{new_value}}, we can evaluate it earlier
                if not tracer_eval_code(condition, **opt):
                    continue

        # in where_clause/update_key, $known's key is mapped to row's column.
        # in key_pattern,  $known's key is also the row's key.
        # column key can have multiple column names. we will use the first defined column
        # to update knowledge
        #  {column=>'TRDQTY,ORDQTY',
        #  clause=>'(TRDQTY={{opt_value}} or ORDQTY={{opt_value}})',
        # }
        kc_column = kc.get('column', k)
        columns = kc_column.split(',')
        code = kc.get('code', None)

        new_value = None
        for column in columns:
            without_prefix = column
            without_prefix = re.sub(r'^.+[.]', '', without_prefix)

            new_value = tpsup.util.get_value_by_key_case_insensitive(
                row, without_prefix, default=None)

            if not new_value and not (code and re.search(r'{{new_value}}', code)):
                # if code is not defined, or defined without using {{value}}, no need $new_value
                print(
                    f"selected row's '{without_prefix}' is not defined.\n")
                continue
            break

        if condition:
            if re.search(r'{{new_value}}', condition):
                if not tracer_eval_code(condition, Dict={**vars, **known, 'new_value': new_value}, **opt):
                    continue

        if code:
            v = tracer_eval_code(
                code, Dict={**vars, **known, 'new_value': new_value}, **opt)
            update_knowledge(k, v, KeyConfig=kc, **opt)
        else:
            if new_value:
                update_knowledge(k, new_value, KeyConfig=kc, **opt)


def update_knowledge(k: str, new_value: str, opt: dict):
    kc = opt.get('KeyConfig', {})
    column = kc.get('column', k)
    known_value = known.get(k, None)

    if known_value is not None:
        mismatch = False

        if kc.get('numeric', False):
            if ',' in known_value:
                known_value = known_value.replace(',', '')
                known[k] = known_value

            mismatch = (known_value != new_value)
        else:
            mismatch = (known_value != new_value)

        if mismatch:
            raise RuntimeError(
                f"conflict at {column}: known='{known_value}', new='{new_value}'")

    else:
        known[k] = new_value
        print(
            f"\nadded knowledge key='{k}' from {column}={pformat(new_value)}\n")

        all_cfg = get_all_cfg(**opt)

        extender = all_cfg['extender_by_key'].get(k, None)
        if extender:
            print(f"\nextending knowledge from key='{k}'\n\n")

            # extender->() is out of this scope, therefore, it  needs to take %known as a variable
            extender(known, k)

    return


def update_error(msg: str, opt: dict):
    known['ERROR_COUNT'] += 1
    known['ERRORS'].append(msg)

    print(f"ERROR: {msg}\n")

    return


def update_ok(msg: str, opt: dict):
    known['OK'].append(msg)

    print(f"OK: {msg}\n")

    return


def update_todo(msg: str, opt: dict):
    known['TODO'].append(msg)

    print(f"TODO: {msg}\n")

    return


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
        today = get_yyyymmdd()
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
        # node = our_cfg/vars/[0]
        # node = our_cfg/vars/[1]
        # node = our_cfg/vars/[2]
        # node = our_cfg/vars/[3]
        re.compile(r'/vars/\[\d*[13579]\]$'),

        # these are all hash keys
        # node = our_cfg/cfg_by_entity/test_code/code
        re.compile(
            r'(condition|code|test|if_fail|if_success|update_knowledge|Exps)$'),
    ]

    temporary_replacement_pattern = re.compile(r'\{\{([0-9a-zA-Z_.-]+)\}\}')

    failed = 0  # restart count

    while node_pairs:
        node = node_pairs.pop(0)
        value = node_pairs.pop(0)

        verbose > 1 and print(f"node = {node}")

        for p in eval_patterns:
            if p.search(node):
                verbose > 1 and print(f"matched {node}")
                clause = value

                # replace all scalar vars {{...}} with 1,
                # but exclude {{pattern::...} and {{where::...}}
                clause = temporary_replacement_pattern.sub(
                    '1', f'{value}', re.MULTILINE)

                if not tpsup.exectools.exec_into_globals(clause,
                                                         globals(), locals(),
                                                         compile_only=1,
                                                         BeginCode=BeginCode,
                                                         verbose=(verbose > 1),
                                                         ):
                    failed += 1
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


def perform_tests(tests: list, **opt):
    verbose = opt.get('verbose', 0)

    if not tests:
        return

    verbose and print("\n---- testing result ----\n\n")

    for item in tests:
        test = item.get('test', None)
        if_success = item.get('if_success', None)
        if_failed = item.get('if_failed', None)
        condition = item.get('condition', None)

        if not test:
            continue

        if condition:
            if not tracer_eval_code(condition, **opt):
                print(f"OK, condition={condition} failed. skipped test\n")
                continue

        if tracer_eval_code(test, **opt):
            verbose and print("test success\n")
            if if_success:
                tracer_eval_code(if_success, **opt)
        else:
            verbose and print("test failed\n")
            if if_failed:
                tracer_eval_code(if_failed, **opt)


my_cfg = None


def set_all_cfg(given_cfg, **opt):
    global my_cfg

    cfg_type = type(given_cfg)

    if cfg_type is str:
        cfg_file = given_cfg
        my_cfg = parse_cfg(cfg_file, **opt)
    elif cfg_type == dict:
        my_cfg = given_cfg
    else:
        raise RuntimeError(
            f"unknown cfg type={cfg_type}, expecting file name (string) or HASH. given_cfg = {given_cfg}")


def get_all_cfg(**opt):
    global my_cfg

    if not my_cfg:
        raise RuntimeError("all_cfg is not defined yet")

    return my_cfg


def reset_global_buffer(**opt):
    global vars
    global lines
    global arrays
    global headers
    global hashes
    global hash1
    global r
    global row_count
    global rc
    global output

    # all these should be reserved words
    all_cfg = get_all_cfg(**opt)

    vars = all_cfg['global_vars']
    lines = []
    arrays = []
    headers = []
    hashes = []
    hash1 = {}
    r = {}
    row_count = 0
    rc = None
    output = None


def print_global_buffer(**opt):
    # mainly for debug purpose
    print("\nprint global buffer \n")
    print(f"vars      = {pformat(vars)}")
    print(f"lines     = {pformat(lines)}")
    print(f"arrays    = {pformat(arrays)}")
    print(f"headers   = {pformat(headers)}")
    print(f"hashes    = {pformat(hashes)}")
    print(f"hash1     = {pformat(hash1)}")
    print(f"r         = {pformat(r)}")
    print(f"row_count = {pformat(row_count)}")
    print(f"rc        = {pformat(rc)}")
    print(f"output    = {pformat(output)}")
    print("\n")


processor_by_method = {
    'code': process_code,
    'db': process_db,
    'cmd': process_cmd,
    'log': process_log,
    'path': process_path,
    'section': process_section,
}

'''
sub process_entity {
   my ($entity, $entity_cfg, $opt) = @_;

   # this pushes back up the setting
   $opt->{verbose} = $opt->{verbose} ? $opt->{verbose} : 0; 
   my $verbose = $opt->{verbose};

   $verbose > 1 && print "$entity entity_cfg = ", Dumper($entity_cfg);

   my $entity_vars = $entity_cfg->{vars};
   if ($entity_vars) {
      $entity_vars = resolve_vars_array($entity_vars, {%vars, %known, entity=>$entity}, $opt);
      $verbose && print "resolved entity=$entity entity_vars=", Dumper($entity_vars);
   } else {
      $entity_vars = {entity=>$entity};
   }

   # we check entity-level condition after resolving entity-level vars.
   # if we need to set up a condition before resolving entity-level vars, do it in
   # the trace_route. If trace_route cannot help, for example, when isExample is true,
   # then convert the var section into using pre_code to update %known

   %vars = (%vars, %$entity_vars);
   $verbose && print "vars = ", Dumper(\%vars);

   my $condition = $entity_cfg->{condition};
   
   if (     defined($condition) 
         # && !$opt->{isExample}     # condition needs to apply to example too
         && !tracer_eval_code($condition, $opt)
      ) {
      print "\nskipped entity=$entity due to failed condition: $condition\n\n";
      return; 
   }

   print <<"EOF";

-----------------------------------------------------------

process $entity

EOF

   my $comment = get_first_by_key([$opt, $entity_cfg], 'comment', {default=>''});
   if ($comment) {
      $comment = resolve_scalar_var_in_string($comment, {%vars, %known}, $opt);
      print "$comment\n\n";
   }

   my $method = $entity_cfg->{method};
   my $processor = $processor_by_method->{$method};

   croak "unsupported method=$method at entity='$entity'" if ! $processor;

   tracer_eval_code($entity_cfg->{pre_code}, $opt) if defined $entity_cfg->{pre_code};

   # $MaxExtracts is different from 'Top'
   #    'Top' is only to limit display
   #    'MaxExtracts' is only to limit memory usage
   #my $MaxExtracts 
   #   = get_first_by_key([$opt, $entity_cfg], 'MaxExtracts', {default=>10000});
   #$opt->{MaxExtracts} = $MaxExtracts;
   $opt->{MaxExtracts} = $opt->{MaxExtracts} ? $opt->{MaxExtracts} : 10000;

   my $method_cfg = $entity_cfg->{method_cfg};

   $processor->($entity, $method_cfg, $opt);

   my $output_key = $entity_cfg->{output_key};
   if ($output_key) {
      # converted from hash array to a single hash
      for my $row (@hashes) {
         my $v = $row->{$output_key};

         if (!defined $v) {
            die "ERROR: output_key=$output_key is not defined in row=", Dumper($row);
         }

         push @{$hash1{$v}}, $row;
      }
   }

   $verbose>1 && print_global_buffer();

   tracer_eval_code($entity_cfg->{code}, $opt) if defined $entity_cfg->{code};

   $verbose>1 && print_global_buffer();

   # should 'example' be applyed by filter?
   #     pro: this can help find specific example
   #     con: without filter, it opens up more example, avoid not finding any example
   #if (!$opt->{isExample}) {
   #   # this affects global variables
   #   apply_csv_filter($entity_cfg->{csv_filter});
   #}
   apply_csv_filter($entity_cfg->{csv_filter}, $opt);

   my $Tail = get_first_by_key([$opt, $entity_cfg], 'tail', {default=>undef});
   my $Top  = get_first_by_key([$opt, $entity_cfg], 'top', {default=>5});

   # display the top results
   if (@lines) {
      print "----- lines begin ------\n";
      #print @lines[0..$Top];  # array slice will insert undef element if beyond range.
      if ($Tail) {
         print @{tail_array(\@lines, $Top)};
      } else {
         print @{top_array(\@lines, $Top)};
      }
      print "----- lines end ------\n";
      print "\n";

      # $row_count is not reliable
      #    - sometime the code forgot updating it
      #    - it is ambiguous: scalar(@lines) and scalar(@hashes) may not be the same.
      my $count = scalar(@lines);
      if ($Tail) {
         print "(Truncated. Total $count, only displayed tail $Tail.)\n" if $count > $Tail;
      } else {
         print "(Truncated. Total $count, only displayed top  $Top.)\n"  if $count > $Top;
      }
   } 

   if (@headers) {
      my $MaxColumnWidth = $entity_cfg->{MaxColumnWidth};
      print "MaxColumnWidth = $MaxColumnWidth\n" if defined $MaxColumnWidth;

      render_csv(\@hashes, \@headers, 
                 {%$opt, 
                   MaxColumnWidth => $MaxColumnWidth,
                  PrintCsvMaxRows =>$Top,
                 });
      print "\n";
      my $count = scalar(@hashes);
      print "(Truncated. Total $count, only displayed top $Top.)\n" if $count > $Top;
   } 
   
   if (@hashes && ($verbose || !@headers)) {
      # we print this only when we didn't print render_csv() or verbose mode
      print Dumper(top_array(\@hashes, $Top));
      print "\n";
      my $count = scalar(@hashes);
      print "(Truncated. Total $count, only displayed top $Top.)\n" if $count > $Top;
   }

   if (!$opt->{isExample}) {
      my $AllowZero    
          = get_first_by_key([$opt, $entity_cfg], 'AllowZero',    {default=>0});
      my $AllowMultiple
          = get_first_by_key([$opt, $entity_cfg], 'AllowMultiple',{default=>0});
   
      if (!$row_count) {
         if ($AllowZero) {
            print "WARN: matched 0 rows. but AllowZero=$AllowZero.\n\n";
         } else {
            print "ERROR: matched 0 rows.\n\n";
            if (exists $entity_cfg->{method_cfg}) {
               print "methond_cfg = ", Dumper($entity_cfg->{method_cfg});
            }
            die "(no need stack trace)";
         }
      } elsif ($row_count >1 ) {
         if ($AllowMultiple) {
            print "WARN:  matched multiple ($row_count) rows, but AllowMultiple=$AllowMultiple, so we will use the 1st one.\n\n";
         } else {
            print "ERROR: matched multiple ($row_count) rows. please narrow your search.\n\n";
            if (exists $entity_cfg->{method_cfg}) {
               print "methond_cfg = ", Dumper($entity_cfg->{method_cfg});
            }
            die "(no need stack trace)";
         }
      } 
   }

   if ($hashes[0]) {
      # only return the first row
      # %r is a global var
      %r = %{$hashes[0]}; 
   }

   if (exists $entity_cfg->{method_cfg}->{where_clause}) {
      my $update_key = unify_hash($entity_cfg->{method_cfg}->{where_clause}, 'column');
      update_knowledge_from_rows(\%r, $update_key, $opt) if $update_key;
   }

   if (exists $entity_cfg->{update_key}) {
      my $update_key = $entity_cfg->{update_key};
      update_knowledge_from_rows(\%r, $update_key, $opt) if $update_key;
   } 
   
   return if $opt->{isExample};

   # update_knowledge first and then run 'tests' and 'post_code', so that they 
   # could use new knowledge
   perform_tests($entity_cfg->{tests}, $opt);  # tests can be undef

   tracer_eval_code($entity_cfg->{post_code}, $opt)
      if defined $entity_cfg->{post_code};

   print "knowledge = ", Dumper(\%known);

   return \%r;
}
'''
# convert above perl code to python


def process_entity(entity, entity_cfg, **opt):
    verbose = opt.get('verbose', 0)

    # this pushes back up the setting
    # opt['verbose'] = verbose

    verbose > 1 and print(f"{entity} entity_cfg = {pformat(entity_cfg)}")

    entity_vars = entity_cfg.get('vars', None)
    if entity_vars:
        entity_vars = resolve_vars_array(
            entity_vars, {**vars, **known, 'entity': entity}, **opt)
        verbose and print(
            f"resolved entity={entity} entity_vars={pformat(entity_vars)}")
    else:
        entity_vars = {'entity': entity}

    # we check entity-level condition after resolving entity-level vars.
    # if we need to set up a condition before resolving entity-level vars, do it in
    # the trace_route. If trace_route cannot help, for example, when isExample is true,
    # then convert the var section into using pre_code to update %known

    global known, our_cfg, row_count, rc, output, lines, arrays, hashes, hash1, r

    # vars are global so that eval/exec can pass data back through them.
    # vars will be reset for each entity, therefore, we don't need to
    # worry about pollution.
    vars.update(entity_vars)
    verbose and print(f"vars = {pformat(vars)}")

    condition = entity_cfg.get('condition', None)

    if condition:
        if not tracer_eval_code(condition, **opt):
            print(
                f"\nskipped entity={entity} due to failed condition: {condition}\n\n")
            return

    print(f'''
-----------------------------------------------------------
          
process {entity}
          ''')

    comment = tpsup.util.get_first_by_key(
        [opt, entity_cfg], 'comment', {'default': ''})
    if comment:
        comment = tpsup.util.resolve_scalar_var_in_string(
            comment, {**vars, **known}, **opt)
        print(f"{comment}\n\n")
    
    method = entity_cfg['method']
    processor = processor_by_method.get(method, None)

    if not processor:
        raise RuntimeError(f"unsupported method={method} at entity='{entity}'")
    
    if pre_code := entity_cfg.get('pre_code', None):
        tracer_eval_code(pre_code, **opt)

    # $MaxExtracts is different from 'Top'
    #    'Top' is only to limit display
    #    'MaxExtracts' is only to limit memory usage
    #my $MaxExtracts
    #   = get_first_by_key([$opt, $entity_cfg], 'MaxExtracts', {default=>10000});
    #$opt->{MaxExtracts} = $MaxExtracts;
    opt['MaxExtracts'] = opt.get('MaxExtracts', 10000)

    method_cfg = entity_cfg.get('method_cfg', None)

    processor(entity, method_cfg, **opt)

    output_key = entity_cfg.get('output_key', None)
    if output_key:
        # converted from hash array to a single hash
        for row in hashes:
            v = row[output_key]

            if v is None:
                raise RuntimeError(
                    f"output_key={output_key} is not defined in row={pformat(row)}")

            hash1.setdefault(v, []).append(row)

    verbose > 1 and print_global_buffer()

    if code := entity_cfg.get('code', None):
        tracer_eval_code(code, **opt)

    verbose > 1 and print_global_buffer()

    # should 'example' be applyed by filter?
    #     pro: this can help find specific example
    #     con: without filter, it opens up more example, avoid not finding any example
    #if (!$opt->{isExample}) {
    #   # this affects global variables
    #   apply_csv_filter($entity_cfg->{csv_filter});
    #}
    apply_csv_filter(entity_cfg.get('csv_filter', None), **opt)

    Tail = tpsup.util.get_first_by_key(
        [opt, entity_cfg], 'tail', {'default': None})
    Top = tpsup.util.get_first_by_key(
        [opt, entity_cfg], 'top', {'default': 5})
    
    # display the top results
    if lines:
        print("----- lines begin ------\n")
        if Tail:
            print(lines[-Tail:])
        else:
            print(lines[:Top])
        print("----- lines end ------\n")
        print("\n")

        # $row_count is not reliable
        #    - sometime the code forgot updating it
        #    - it is ambiguous: scalar(@lines) and scalar(@hashes) may not be the same.
        count = len(lines)
        if Tail:
            print(
                f"(Truncated. Total {count}, only displayed tail {Tail}.)\n") if count > Tail
        else:
            print(
                f"(Truncated. Total {count}, only displayed top  {Top}.)\n") if count > Top

    if headers:
        MaxColumnWidth = entity_cfg.get('MaxColumnWidth', None)
        print(f"MaxColumnWidth = {MaxColumnWidth}") if MaxColumnWidth else None

        tpsup.util.render_csv(hashes, headers,
                              {**opt,
                               'MaxColumnWidth': MaxColumnWidth,
                               'PrintCsvMaxRows': Top,
                               })
        print("\n")
        count = len(hashes)
        if count > Top:
            print(f"(Truncated. Total {count}, only displayed top {Top}.)\n")

    if hashes and (verbose or not headers):
        # we print this only when we didn't print render_csv() or verbose mode
        print(hashes[:Top])
        print("\n")
        count = len(hashes)
        if count > Top:
            print(f"(Truncated. Total {count}, only displayed top {Top}.)\n")

    if not opt.get('isExample', False):
        AllowZero = tpsup.util.get_first_by_key(
            [opt, entity_cfg], 'AllowZero', {'default': 0})
        AllowMultiple = tpsup.util.get_first_by_key(
            [opt, entity_cfg], 'AllowMultiple', {'default': 0})
        
        if not row_count:
            if AllowZero:
                print("WARN: matched 0 rows. but AllowZero=$AllowZero.\n\n")
            else:
                print("ERROR: matched 0 rows.\n\n")
                if 'method_cfg' in entity_cfg:
                    print(f"methond_cfg = {pformat(entity_cfg['method_cfg'])}")
                raise RuntimeError("(no need stack trace)")
        elif row_count > 1:
            if AllowMultiple:
                print(
                    f"WARN:  matched multiple ({row_count}) rows, but AllowMultiple={AllowMultiple}, so we will use the 1st one.\n\n")
            else:
                print(
                    f"ERROR: matched multiple ({row_count}) rows. please narrow your search.\n\n")
                if 'method_cfg' in entity_cfg:
                    print(f"methond_cfg = {pformat(entity_cfg['method_cfg'])}")
                raise RuntimeError("(no need stack trace)")
            
    if hashes[0]:
        # only return the first row
        # %r is a global var
        r = hashes[0]

    if update_key := tpsup.util.unify_hash_hash(entity_cfg.get('method_cfg', {}).get('where_clause', {}), 'column'):
        update_knowledge_from_rows(r, update_key, **opt)
    if update_key := entity_cfg.get('update_key', None):
        update_knowledge_from_rows(r, update_key, **opt)

    if opt.get('isExample', False):
        return
    
    # update_knowledge first and then run 'tests' and 'post_code', so that they
    # could use new knowledge
    perform_tests(entity_cfg.get('tests', []), **opt)  # tests can be undef

    if post_code := entity_cfg.get('post_code', None):
        tracer_eval_code(post_code, **opt)

    print(f"knowledge = {pformat(known)}")

    return r


        

        

def trace(given_cfg, input, **opt):
    verbose = opt.get('verbose', 0)

    set_all_cfg(given_cfg, **opt)

    all_cfg = get_all_cfg(**opt)

    verbose > 1 and print(f"all_cfg = {pformat(all_cfg)}")

    cfg_by_entity = all_cfg['cfg_by_entity']
    entry_points = all_cfg.get('entry_points', [])
    trace_route = all_cfg.get('trace_route', [])

    if TraceString := opt.get('TraceString', None):
        selected_entities = TraceString.split(',')

        new_trace_route = []

        for e in selected_entities:
            # if the entity is already in the configured trace route, add it with the config.
            for t in trace_route:
                if e == t['entity']:
                    new_trace_route.append(t)
                    continue

            # if the entity is not in the configured trace route, add it here.
            new_trace_route.append({'entity': e})

        trace_route = new_trace_route  # set new trace route
        entry_points = []            # we skip all entry points too

        verbose and print(f"trace_route = {pformat(trace_route)}")
        verbose and print(f"entry_points = {pformat(entry_points)}")

    parsed_input = parse_input(input,
                               AliasMap=all_cfg['alias_map'],
                               AllowedKeys=all_cfg['allowed_keys'],
                               )

    # these keys has precedence to populate because extender func may need this info.
    for k in ['YYYYMMDD']:
        if parsed_input.get(k, None):
            update_knowledge(k, parsed_input[k])

    if 'YYYYMMDD' in all_cfg['allowed_keys']:
        today = get_yyyymmdd()
        if not known.get('YYYYMMDD', None):
            update_knowledge('YYYYMMDD', today)
        update_knowledge('TODAY', today)

    for k in parsed_input.keys():
        update_knowledge(k, parsed_input[k])

    verbose and print(f"knowledge from input = {pformat(known)}")

    if vars := all_cfg.get('vars', None):
        global_vars = resolve_vars_array(vars, known, **opt)
        all_cfg['global_vars'] = global_vars
    else:
        all_cfg['global_vars'] = {}

    verbose and print(f"global_vars = {pformat(all_cfg['global_vars'])}")

    if known.get('EXAMPLE', None):
        entity = known['EXAMPLE']
        entity_cfg = tpsup.util.get_value_by_key_case_insensitive(
            cfg_by_entity, entity, **opt)

        opt2 = {**opt,
                'AllowMultiple': 1,  # not abort when multiple results
                'Top': 5,            # display upto 5 results
                'isExample': 1,
                }

        # only reset buffer not $known neither global cfg
        reset_global_buffer(**opt)
        vars['entity'] = entity

        process_entity(entity, entity_cfg, **opt2)

        verbose and print(f"knowledge = {pformat(known)}")
        return

    SkipTrace = {}
    if SkipTraceString := opt.get('SkipTrace', None):
        if (re.match(r'^all$', SkipTraceString, re.IGNORECASE)):
            trace_route = []
        else:
            for t in SkipTraceString.split(','):
                SkipTrace[t] = 1

            verbose and print(f"SkipTrace = {pformat(SkipTrace)}")

    ForceThrough = opt.get('ForceThrough', False)
    # todo - do we still need this in python

    result = {}

    if trace_route and not opt.get('SkipEntry', False) and entry_points:
        for row in entry_points:
            keys, entities = row

            for k in keys:
                if (k not in known) or (known[k] is None):
                    continue

            verbose and print(
                f"matched entry point: {pformat(keys)} {pformat(entities)}")

            for entity in entities:
                if entity in SkipTrace:
                    continue

                entity_cfg = tpsup.util.get_value_by_key_case_insensitive(
                    cfg_by_entity, entity, **opt)

                try:
                    result[entity] = process_entity(entity, entity_cfg, **opt)
                except Exception as e:
                    # don't print stack trace for easy understanding errors.
                    if not re.search(r'\(no need stack trace\)', e):
                        print(e)
                    if not ForceThrough:
                        raise RuntimeError(
                            f"entity={entity} failed. aborting")

            break  # only process the first match in entry point

    trace_route_entities = tpsup.util.get_keys_from_array(
        trace_route, 'entity')

    if not trace_route_entities:
        print("\n\nnothing to trace\n\n")
        return

    verbose and print(f"\n\nstart tracing: {trace_route_entities}\n\n")

    for row in trace_route:
        entity = row['entity']
        opt2 = {**opt, **row}

        if entity in SkipTrace:
            continue

        if entity in result and not row['reentry']:
            print(f"entity={entity} had been traced before\n")
            continue

        # only reset buffer not $known neither global cfg
        reset_global_buffer(**opt)
        vars['entity'] = entity

        if condition := row.get('condition', None):
            if not tracer_eval_code(condition, **opt):
                continue

        entity_cfg = tpsup.util.get_value_by_key_case_insensitive(
            cfg_by_entity, entity, **opt)

        try:
            result[entity] = process_entity(entity, entity_cfg, **opt2)
        except Exception as e:
            if not re.search(r'\(no need stack trace\)', e):
                print(e)
            if not ForceThrough:
                raise RuntimeError(f"entity={entity} failed. aborting")


yyyymmdd = None


def get_yyyymmdd(**opt):
    global yyyymmdd

    if not yyyymmdd:
        yyyymmdd = strftime("%Y%m%d", localtime())

    return yyyymmdd


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
