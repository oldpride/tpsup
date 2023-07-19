import re
from pprint import pformat
from typing import Dict, List, Union, Callable

import tpsup.util


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


# convert this perl to python
# sub resolve_a_clause {
#    my ($clause, $Dict, $opt) = @_;

#    # first substitute the scalar var in {{...}}
#    $opt->{verbose} && print "line ", __LINE__, " before substitution, clause = $clause, Dict = ", Dumper($Dict);

#    $clause = resolve_scalar_var_in_string($clause, $Dict, $opt);

#    $opt->{verbose} && print "line ",__LINE__, " after substitution, clause = $clause\n";

#    # we don't need this because we used 'our' to declare %known.
#    # had we used 'my', we would have needed this.
#    #my $touch_to_activate = \%known;

#    # then eval() other vars, eg, $known{YYYYMMDD}
#    my $clause2 = tracer_eval_code($clause, {%$opt, Dict=>$Dict});

#    return $clause2;
# }

# convert above to python
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

# convert below perl to python
#
