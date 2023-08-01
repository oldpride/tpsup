import inspect
import os
import re
from pprint import pformat
from time import localtime, strftime, strptime
from typing import Dict, List, Union, Callable

import tpsup.util
import tpsup.cmdtools
import tpsup.exectools
import tpsup.csvtools
import tpsup.print
# import tpsup.tplog
from tpsup.tplog import log_FileFuncLine, get_stack
import tpsup.sqltools

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
        if re.match(r'any|check', pair, re.IGNORECASE):
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

    check_allowed_keys(ref, opt.get('AllowedKeys', []), **opt)

    return ref


def check_allowed_keys(href: dict, list: list, **opt):
    # check ref is empty
    if not href:
        return

    # use upper case to avoid case-sensitive issue
    allowed = {key.upper(): 1 for key in list}

    for key in href.keys():
        if key.upper() not in allowed:
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


def resolve_a_clause(clause: str, dict1: dict, **opt):
    verbose = opt.get('verbose', 0)

    # in python, both dict and Dict are reserved words.
    # therefore, we use dict1 instead of dict or Dict.

    # first substitute the scalar var in {{...}}
    verbose > 1 and log_FileFuncLine(
        f"before substitution, clause = {clause}, dict1 = {pformat(dict1)}")

    clause = tpsup.util.resolve_scalar_var_in_string(clause, dict1, **opt)

    verbose > 1 and log_FileFuncLine(f"after substitution, clause = {clause}")

    # we don't need this because we used 'our' to declare %known.
    # had we used 'my', we would have needed this
    # my $touch_to_activate = \%known;

    # then eval() other vars, eg, $known{YYYYMMDD}
    clause2 = tracer_eval_code(clause, **{**opt, 'dict1': dict1})

    return clause2


def resolve_vars_array(vars: list, dict1: dict, **opt):
    # vars in our_cfg is a ref to array. This is for enforcing the order.
    # vars in global is a hash (dict). this is for easy access.
    # therefore, we need to convert array to hash.
    verbose = opt.get('verbose', 0)

    if verbose > 1:
        log_FileFuncLine(f'opt =\n{pformat(opt)}')

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

        if not isinstance(k, str):
            raise Exception(
                f"key type is not string. k = {k}, in vars = {vars}")

        if not isinstance(v, str):
            raise Exception(
                f"value type is not string. v = {v}, in vars = {vars}")

        v2 = resolve_a_clause(v, dict2, **opt)

        ref[k] = v2
        if verbose > 1:
            print(f"added var key='{k}' from {v}={pformat(v2)}\n")
        dict2[k] = v2  # previous variables will be used to resolve later variables

    return ref


def cmd_output_string(cmd: str, **opt):
    string = tpsup.cmdtools.run_cmd_clean(cmd, **opt)
    return string


def process_code(entity: str, method_cfg: dict, **opt):
    # all handling have been done by caller, process_entity
    return


compiled_where_by_key = {}
decommify_pattern = re.compile(r',')


def craft_sql(entity: str, method_cfg: dict, dict1: dict, **opt):
    global vars, lines, arrays, headers, hashes, hash1, r, row_count, rc, output
    footer = ""
    MaxExtracts = opt.get('MaxExtracts', None)
    template = method_cfg.get('template', None)

    if template:
        # for example

        # select  *
        # from (
        #   select
        #     PosQty - LAG(PosQty, 1, 0) OVER (Order By LastUpdateTime) as TradeQty,
        #     '{{YYYYMMDD}}' as day,
        #     *
        #    from
        #     Position (nolock)
        #   where
        #     1 = 1
        #     {{where::YYYYMMDD}}
        #     {{where::ACCOUNT}}
        #     {{where::SECURITYID}}
        #     {{where::LE}}
        #     and PosQty is not null
        #   )
        # where
        #   1=1
        #   {{where::QTY}}

        # will be resolved to

        # select  *
        # from (
        #   select
        #     PosQty - LAG(PosQty, 1, 0) OVER (Order By LastUpdateTime) as TradeQty,
        #     '20211101' as day,
        #     *
        #    from
        #     Position (nolock)
        #   where
        #     TradeDate = '20211101'
        #     and Account = 'BLK12345'
        #     and SecurityId = '437855'
        #     and LegalEntity = 'ABC'
        #     and PosQty is not null
        #   )
        # where TradeQty = 2000

        # note:
        #   use where:: to difference regular var to be replaced by $dict and var to
        #   be replaced by where_clause. YYYYMMDD above is an example
        # default template is shown below
        pass
    else:
        table = method_cfg.get('table', entity)

        db_type = method_cfg.get('db_type', None)

        # nolock setting is easy in MSSQL using DBD
        #
        # however, for mysql, i am not sure what to do yet
        #
        # i followed the following two links
        #    https://stackoverflow.com/questions/917640/any-way-to-select-without-causing-locking-in-mysql
        #    https://www.perlmonks.org/?node_id=1074673

        mssql_specific1 = ""
        mssql_specific2 = ""

        mysql_specific1 = ""

        is_mssql = False
        is_mysql = False

        if db_type:
            if re.search('mssql', db_type, re.IGNORECASE):
                is_mssql = True

                mssql_specific1 = f"top {MaxExtracts}"
                mssql_specific2 = 'with (nolock)'
            elif re.search('mysql', db_type, re.IGNORECASE):
                is_mysql = True

                mysql_specific1 = f"LIMIT {MaxExtracts};"

        header = method_cfg.get('header', '*')
        # header's function can be replaced by template
        # example
        #    table  => 'mytable',
        #    header => 'count(*) as TotalRows',
        #    where_clause => { YYYYMMDD => 'TradeDate' },
        # can be replaced by
        #    template => '
        #       select count(*) as TotalRows
        #         from mytable
        #         where 1=1
        #               {{where::YYYYMMDD}}
        #    ',
        #    where_clause => { YYYYMMDD => 'TradeDate' },

        # this is the default template
        template = f"""
        select {mssql_specific1} {header}
            from {table} {mssql_specific2}
              where 1 = 1""" + """
        {{where_clause}}
        """
        footer = f"{mysql_specific1}"

    wc = method_cfg.get('where_clause', None)

    where_block = ""
    if wc:
        for key in sorted(wc.keys()):
            opt_value = tpsup.util.get_first_by_key(
                [opt, dict1], key, default=None)
            if opt_value is None:
                if compiled_where := compiled_where_by_key.get(key, None):
                    pass
                else:
                    # compile the {{where::key}} pattern
                    compiled_where = re.compile(f'{{{{where::{key}}}}}')
                    compiled_where_by_key[key] = compiled_where
                # erase the clause
                template = compiled_where.sub('', template)
                continue

            info = wc[key]
            info_type = type(info)

            string = None

            if info_type is dict:
                clause, column, numeric, if_exp, else_clause = info.get(
                    'clause', None), info.get('column', None), info.get('numeric', None), info.get('if_exp', None), info.get('else_clause', None)

                if if_exp is not None:
                    if not tracer_eval_code(if_exp, **opt):
                        if else_clause is not None:
                            # if 'if_exp' is defined and is false and 'else_clause' is defined,
                            # then use else_clause as clause
                            clause = else_clause
                        else:
                            continue

                if clause:
                    clause = tpsup.util.resolve_scalar_var_in_string(
                        clause, {**dict1, 'opt_value': opt_value}, **opt)
                    string = f"and {clause}"
                elif column is None:
                    column = key
            else:
                column = info

            if not string:
                if numeric:
                    opt_value = decommify_pattern.sub(
                        '', opt_value)  # decommify
                    string = f"and {column} =  {opt_value}"
                else:
                    string = f"and {column} = '{opt_value}'"

            where_block += f"             {string}\n"
            template = compiled_where.sub(string, template)

    template = template.replace('{{where_clause}}', where_block)

    if opt.get('isExample', None):
        ec = method_cfg.get('example_clause', None)
        if ec:
            template += f"             and {ec}\n"

    extra_clause = method_cfg.get('extra_clause', None)
    if extra_clause:
        template += f"             and {extra_clause}\n"

    sql = template

    TrimSql = tpsup.util.get_first_by_key(
        [opt, method_cfg], 'TrimSql', default=None)
    if TrimSql:
        # make Trim optional because it is actually easier to modify the sql with \
        # the '1=1' - we only need to comment out a unneeded clause with '--'

        # trim unnecessary where clause
        if re.search(r'where 1 = 1\n$', sql, re.MULTILINE):             # multiline regex
            # trim
            #       select  *
            #         from tblMembers
            #        where 1 = 1
            #  to
            #
            #       select  *
            #         from tblMembers

            sql = re.sub(r'[^\n]*where 1 = 1\n$', '', sql,
                         flags=re.MULTILINE)        # multiline regex
        elif re.search(r'where 1 = 1\n\s*and', sql, re.MULTILINE):   # multiline regex
            # trim
            #       select  *
            #         from tblMembers
            #        where 1 = 1
            #              and lastname = 'Tianhua'
            #  to
            #
            #       select  *
            #         from tblMembers
            #        where lastname = 'Tianhua'

            sql = re.sub(r'where 1 = 1\n\s*and', 'where ', sql,
                         flags=re.MULTILINE)   # multiline regex

    order_clause = method_cfg.get('order_clause', None)
    if order_clause:
        sql += f"             {order_clause}\n"

    sql += footer

    # resolve the rest scalar vars at the last moment to avoid resolve where_clause vars.
    resolved_sql = tpsup.util.resolve_scalar_var_in_string(sql, dict1, **opt)

    return resolved_sql


def process_db(entity: str, method_cfg: dict, **opt):
    global vars, lines, arrays, headers, hashes, hash1, r, row_count, rc, output

    verbose = opt.get('verbose', 0)

    table = method_cfg.get('table', entity)

    sql = craft_sql(table, method_cfg, {**vars, **known}, **opt)

    db_type = method_cfg.get('db_type', None)
    db = method_cfg.get('db', None)

    is_mysql = False
    if db_type:
        if re.search('mysql', db_type, re.IGNORECASE):
            is_mysql = True

    dbh = tpsup.sqltools.get_dbh(nickname=db)
    if is_mysql:
        dbh.autocommit = False  # Disable global leverl, so we can SET FOR TRANSACTION LEVEL

        mysql_setting = 'SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED ;'
        print(f"{mysql_setting}\n\n")
        # if is_statement=true, no rows will be returned from run_sql()
        tpsup.sqltools.run_sql(mysql_setting, dbh=dbh, is_statement=True)

    print(f"sql {db} \"{sql}\"\n\n")
    result: list = tpsup.sqltools.run_sql(sql, dbh=dbh, RenderOutput=verbose,
                                          ReturnType='ListList',  # array of arrays. 1st row is header
                                          ReturnDetail=True,
                                          )

    verbose > 1 and log_FileFuncLine(f"result = {pformat(result)}\n\n")

    if is_mysql:
        mysql_setting = 'COMMIT ;'
        print(f"{mysql_setting}\n\n")
        tpsup.sqltools.run_sql(mysql_setting, dbh=dbh, is_statement=True)

    if result and len(result) > 0:
        # set the global buffer for post_code
        arrays = result[1:]
        headers = result[0]
        hashes = tpsup.util.arrays_to_hashes(arrays, headers)
        row_count = len(arrays)


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


def update_knowledge(k: str, new_value: str, **opt):
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
    our_cfg['vars'] = ['cfgdir', f"r'{cfgdir}'",
                       'cfgname', f"r'{cfgname}'"] + our_cfg['vars']
    # use r'' to avoid backslash issue
    #    File "our_cfg node=our_cfg/vars/[1]", line 3
    #       'C:\users\william\sitebase\github\tpsup\python3\lib\tpsup'
    #       SyntaxError: (unicode error) 'unicodeescape' codec can't decode
    #           bytes in position 2-3: truncated \uXXXX escape

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
    # 'vars' is not in above because we will replace it with '1' to test compilation.
    # when we test compile, we will replace all {{...}} with '1' to avoid syntax error.
    # {{...}} comes from 'vars' and 'known'. but we keep 'known' because known[key] can exist.

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

                if not tpsup.exectools.test_compile(clause,
                                                    globals(), locals(),
                                                    source_filename=f'our_cfg node={node}',
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
    global vars, lines, arrays, headers, hashes, hash1, r, row_count, rc, output
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
    global vars, lines, arrays, headers, hashes, hash1, r, row_count, rc, output
    print()
    print(f"{get_stack(2)}: print global buffer")
    print("----------------------------------------")
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
    # 'cmd': process_cmd,
    # 'log': process_log,
    # 'path': process_path,
    # 'section': process_section,
}


def process_entity(entity, entity_cfg, **opt):
    verbose = opt.get('verbose', 0)

    global vars, lines, arrays, headers, hashes, hash1, r, row_count, rc, output

    # this pushes back up the setting
    # opt['verbose'] = verbose

    verbose > 1 and print(f"{entity} entity_cfg = {pformat(entity_cfg)}")

    if 'vars' in entity_cfg:
        # entity_cfg['vars'] is an array, in order to enforce the order.
        # entity_vars is a hash (dict), for easy access.
        # therefore, we need to convert array to hash.
        entity_vars = resolve_vars_array(
            entity_cfg['vars'], {**vars, **known, 'entity': entity}, **opt)
        verbose and print(
            f"resolved entity={entity} entity_vars={pformat(entity_vars)}")
    else:
        entity_vars = {'entity': entity}

    # we check entity-level condition after resolving entity-level vars.
    # if we need to set up a condition before resolving entity-level vars, do it in
    # the trace_route. If trace_route cannot help, for example, when isExample is true,
    # then convert the var section into using pre_code to update %known

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
        [opt, entity_cfg], 'comment', default='')
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
    # my $MaxExtracts
    #   = get_first_by_key([$opt, $entity_cfg], 'MaxExtracts', {default=>10000});
    # $opt->{MaxExtracts} = $MaxExtracts;
    opt['MaxExtracts'] = opt.get('MaxExtracts', 10000)

    method_cfg = entity_cfg.get('method_cfg', None)

    processor(entity, method_cfg, **opt)
    # this sets all the global variables

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
    # if (!$opt->{isExample}) {
    #   # this affects global variables
    #   apply_csv_filter($entity_cfg->{csv_filter});
    # }
    apply_csv_filter(entity_cfg.get('csv_filter', None), **opt)

    Tail = tpsup.util.get_first_by_key(
        [opt, entity_cfg], 'tail', default=None)
    Top = tpsup.util.get_first_by_key(
        [opt, entity_cfg], 'top', default=5)

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
            if count > Tail:
                print(
                    f"(Truncated. Total {count}, only displayed tail {Tail}.)\n")
        else:
            if count > Top:
                print(
                    f"(Truncated. Total {count}, only displayed top  {Top}.)\n")

    if headers:
        MaxColumnWidth = entity_cfg.get('MaxColumnWidth', None)
        print(f"MaxColumnWidth = {MaxColumnWidth}") if MaxColumnWidth else None

        tpsup.print.render_arrays(hashes,
                                  MaxColumnWidth=MaxColumnWidth,
                                  MaxRows=Top,
                                  RenderHeader=1
                                  )
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
            [opt, entity_cfg], 'AllowZero', default=0)
        AllowMultiple = tpsup.util.get_first_by_key(
            [opt, entity_cfg], 'AllowMultiple', default=0)

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

    if 0 < len(hashes):  # test array index existence
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


def apply_csv_filter_href(filter1: Union[dict, None], **opt):
    if not filter1:
        return

    # example of $filter1:
    #            {
    #             ExportExps => [
    #                'weight=$STATUS eq "COMPLETED" ? 0 : $STATUS eq "PARTIAL" ? 1 : 2',
    #                ],
    #              SortKeys => [ 'weight' ],
    #            },

    filter2 = {}
    changed = False
    for k in sorted(filter1.keys()):
        if 'Exps' in k:
            Exps1 = filter1[k]

            # Exps1 should be an array or None
            if not Exps1:
                continue

            if not isinstance(Exps1, list):
                raise RuntimeError(
                    f"wrong type={type(Exps1)}. Only list is supported")

            Exps2 = []
            for e1 in Exps1:
                e2 = tpsup.util.resolve_scalar_var_in_string(
                    e1, {**vars, **known}, **opt)
                e2 = apply_key_pattern(e2, **opt)

                changed = (e2 != e1)
                Exps2.append(e2)

            filter2[k] = Exps2
        else:
            filter2[k] = filter1[k]

    if changed:
        print(f"original filter1 = {pformat(filter1)}")
        print(f"resolved filter2 = {pformat(filter2)}")
    else:
        print(f"static filter2 = {pformat(filter2)}")

    return filter2


def apply_csv_filter(filters: Union[list, dict, None], **opt):
    if not filters:
        return

    # examples:
    # can be array, which depending knowledge keys
    # $csv_filter => [
    #          [
    #            [ ], # depending keys, like entry_points
    #            {
    #             ExportExps => [
    #                'weight=$STATUS eq "COMPLETED" ? 0 : $STATUS eq "PARTIAL" ? 1 : 2',
    #                ],
    #              SortKeys => [ 'weight' ],
    #            },
    #          ]
    #       ],
    # can be Hash
    # $csv_filter =>
    #       {
    #          ExportExps => [
    #             'weight=$STATUS eq "COMPLETED" ? 0 : $STATUS eq "PARTIAL" ? 1 : 2',
    #             ],
    #          SortKeys => [ 'weight' ],
    #       },

    global vars, lines, arrays, headers, hashes, hash1, r, row_count, rc, output

    filter3 = {}
    for row in filters:
        keys, href = row

        all_keys_known = True
        for k in keys:
            if k not in known:
                all_keys_known = False
                break
        if not all_keys_known:
            continue

        filter4 = apply_csv_filter_href(href, **opt)
        filter3 = {**filter3, **filter4}

    if isinstance(filters, list):
        # if $type was HASH, it was already printed by apply_csv_filter()
        # if $type was ARRAY, we print the finalized filter
        print(f"filter3 = {pformat(filter3)}")

    MaxRows = opt.get('MaxExtracts', None)

    hashes2 = tpsup.csvtools.filter_dicts(hashes, headers,
                                          **filter3
                                          )
    # update global buffer
    hashes = hashes2
    if hashes:
        headers = hashes[0].keys()
        tpsup.print.render_arrays(hashes,
                                  MaxRows=MaxRows,
                                  RenderHeader=1,
                                  )
    else:
        headers = []
    arrays = tpsup.util.hashes_to_arrays(hashes, headers)
    row_count = len(hashes)

    return  # this sub affects global buffer, therefore, nothing to return


scalar_key_pattern = None


def apply_key_pattern(string: str, **opt):
    # line_pattern => 'orderid=(?<ORDERID>{{pattern::ORDERID}}),.*tradeid=(?<TRADEID>{{pattern::TRADEID}}),.*sid=(?<SID>{{pattern::SID}}),.*filledqty=(?<FILLEDQTY>{{pattern::FILLEDQTY}}),',

    # scalar_key_pattern = r'\{\{pattern::([0-9a-zA-Z_.-]+)\}\}'
    # needed_keys = re.findall(scalar_key_pattern, string)
    global scalar_key_pattern
    if not scalar_key_pattern:
        scalar_key_pattern = re.compile(r'\{\{pattern::([0-9a-zA-Z_.-]+)\}\}')

    needed_keys = scalar_key_pattern.findall(string)

    all_cfg = get_all_cfg(**opt)

    key_pattern = all_cfg['key_pattern']

    for k in needed_keys:
        if k not in key_pattern:
            raise RuntimeError(
                f"'{{pattern::{k}}}' in '{string}' but '{k}' is not defined in key_pattern={pformat(key_pattern)}")

    global known
    for k in needed_keys:
        substitue = known.get(k, key_pattern[k]['pattern'])
        string = re.sub('{{pattern::'+f'{k}' + '}}', substitue, string)

    return string


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

    if 'vars' in all_cfg:
        # all_cfg['vars'] is from the config file, it is an array, in order to enforce the order.
        # vars and known are global hash, for each access. so is all_cfg['global_vars'].
        # therefore, we need to convert all_cfg['vars'] into a hash.
        global_vars = resolve_vars_array(all_cfg['vars'], known, **opt)
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

        row2 = {k: v for k, v in row.items() if k != 'entity'}
        opt2 = {**opt, **row2}

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

        success = 0
        try:
            result[entity] = process_entity(entity, entity_cfg, **opt2)
            success = 1
        except Exception as e:
            if not re.search(r'no need stack trace', f'{e}', re.MULTILINE):
                print(f"exception detail={e}")

        if not success:
            if not ForceThrough:
                # raise RuntimeError(f"entity={entity} failed. aborting")
                exit(1)


yyyymmdd = None


def get_yyyymmdd(**opt):
    global yyyymmdd

    if not yyyymmdd:
        yyyymmdd = strftime("%Y%m%d", localtime())

    return yyyymmdd


def tracer_eval_code(code: str, **opt):
    verbose = opt.get('verbose', 0)

    if verbose > 1:
        log_FileFuncLine(f"opt = {pformat(opt)}")

    global vars
    global known

    # this relies on global buffer that are specific to TPSUP::TRACER
    # default dictionary is vars, known.
    # if user specifies dict1, then it will be used to resolve {{key}}.
    #     but user can still vars and known in this form: known['key'] or vars['key'].
    # if user doesn't specify dict1, then vars and known will be used to resolve {{key}}.
    dict1 = opt.get('dict1', {**vars, **known})

    if verbose > 1:
        print()
        log_FileFuncLine(f"original code={code}")

    code = tpsup.util.resolve_scalar_var_in_string(
        code, dict1, verbose=(verbose > 1))

    if verbose > 1:
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
    # print(f'parse_cfg(cfg_file) = {pformat(parse_cfg(cfg_file))}')
    trace(cfg_file, ['sec=IBM.N', 'yyyymmdd=20211129'], verbose=0)


if __name__ == '__main__':
    main()
