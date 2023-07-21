import inspect
import re
from pprint import pformat
from typing import Dict, List, Union, Callable

import tpsup.util
import tpsup.cmdtools


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

    for k in opt.get("key_pattern", []):
        seen[k.upper()] = 1

    return seen.keys()


def __line__():
    return __line__
    return inspect.currentframe().f_back.f_lineno


def __file__():
    return __file__


def resolve_a_clause(clause: str, Dict: dict, **opt):
    # first substitute the scalar var in {{...}}
    opt['verbose'] and print(
        f"line {__line__()} before substitution, clause = {clause}, Dict = {pformat(Dict)}")

    clause = tpsup.util.resolve_scalar_var_in_string(clause, Dict, **opt)

    opt['verbose'] and print(
        f"line {__line__()} after substitution, clause = {clause}")

    # we don't need this because we used 'our' to declare %known.
    # had we used 'my', we would have needed this.
    # my $touch_to_activate = \%known;

    # then eval() other vars, eg, $known{YYYYMMDD}
    clause2 = tracer_eval_code(clause, Dict=Dict, **opt)

    return clause2


def resolve_vars_array(vars: list, Dict: dict, **opt):
    if not vars:
        return {}

    # vars is a ref to array.
    if not isinstance(vars, list):
        raise Exception(f"vars type is not list. vars = {vars}")

    ref = {}

    # copy to avoid modifying original data
    Dict2 = {}
    Dict2.update(Dict)
    vars2 = vars.copy()

    while vars2:
        k = vars2.pop(0)
        v = vars2.pop(0)

        v2 = resolve_a_clause(v, Dict2, **opt)

        ref[k] = v2
        Dict2[k] = v2  # previous variables will be used to resolve later variables

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

'''
sub tracer_eval_code {
   my ($code, $opt) = @_;

   my $verbose = $opt->{verbose} ? $opt->{verbose} : 0;

   # this relies on global buffer that are specific to TPSUP::TRACER
   # default dictionary is {%vars, %known}
   my $dict = $opt->{Dict} ? $opt->{Dict} : {%vars, %known};

   if ($verbose) {
      print "------ begin preparing code ------\n";
      print "original code: $code\n";
   }

   $code = resolve_scalar_var_in_string($code, $dict, $opt);

   if ($verbose) {
      print "afer substituted scalar vars in '{{...}}': $code\n";
      eval "no warnings;
            print qq(after eval'ed code: $code\n);
            use warnings;
           ";
   }

   # use a sub{} to separate compile-time error and run-time error
   #    compile-time error should be handled right here
   #        run-time error should be handled by caller

   my $func;
   eval "\$func = sub { $code }";
   if ($@) {
      # compile-time error happens here
      my $numbered_code = add_line_number_to_code($code);
      croak "failed to compile code='
$numbered_code
$@
      '\n" ;
   }
   $func->();     # run-time error happens here
}
'''
