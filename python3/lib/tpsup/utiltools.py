from pprint import pformat
import re
from typing import Literal
from tpsup.logbasic import log_FileFuncLine


def get_value_by_key_case_insensitive(value_by_key: dict, key: str, **opt):
    verbose = opt.get("verbose", 0)
    if verbose > 1:
        log_FileFuncLine(f"value_by_key = {pformat(value_by_key)}")

    if not value_by_key:
        return None

    if key in value_by_key:
        return value_by_key[key]

    uc_key = key.upper()

    for k, v in value_by_key.items():
        if uc_key == k.upper():
            return v

    if "default" in opt:
        return opt["default"]
    else:
        raise Exception(
            f"key={key} has no match even if case-insensitive in {pformat(value_by_key)}")


def get_first_by_key(array_of_hash: list, key: str, **opt):
    if not array_of_hash:
        return None

    CaseSensitive = opt.get("CaseSensitive", False)

    for h in array_of_hash:
        if not h:
            continue

        if CaseSensitive:
            if value := h.get(key, None):
                return value
        else:
            # try case in-sensitive
            v = None
            try:
                v = get_value_by_key_case_insensitive(h, key)
            except Exception as e:
                pass
            if v is not None:
                return v

    return opt.get("default", None)


def resolve_scalar_var_in_string(clause: str, dict1: dict, **opt):
    # in python, both dict and Dict are reserved words.
    # therefore, we use dict1 instead of dict or Dict.

    # print(f"opt = {opt}")
    verbose = opt.get("verbose", 0)

    if not clause:
        return clause

    if verbose > 1:
        log_FileFuncLine(f"clause = {clause}")

    # scalar_vars is enclosed by double curlies {{...=default}},
    # but exclude {{pattern::...} and {{where::...}}.
    # there are 2 '?':
    #    the 1st '?' is for ungreedy match
    #    the 2nd '?' says the (...) is optional
    # example:
    #    .... {{VAR1=default1}}|{{VAR2=default2}}
    # default can be multi-line
    # default will be undef in the array if not defined.

    vars_defaults = re.findall(r"{{([0-9a-zA-Z._-]+)(=.{0,200}?)?}}", clause, re.MULTILINE)

    if verbose > 1:
        log_FileFuncLine(f"vars_defaults = {vars_defaults}")
        # "{{v1}} and {{v2}} and {{v3=abc}}" => [('v1', ''), ('v2', ''), ('v3', '=abc')]

    if not vars_defaults:
        # return when no variable found, because nothing will change.
        return clause

    if verbose > 1:
        log_FileFuncLine(f"vars_defaults = {vars_defaults}")
        # vars_defaults may have dup.
        # when there is no default defined, default is ''.
        # vars_defaults = [('prog', ''), ('A0', ''), ('A1', ''), ('prog', '')]

    defaults_by_var = {}
    scalar_vars = []
    for vd in vars_defaults:
        var, default = vd
        if default:
            default = default[1:]  # remove the leading '='
        scalar_vars.append(var)
        if var in defaults_by_var:
            defaults_by_var[var].append(default)
        else:
            defaults_by_var[var] = [default]

    if verbose > 1:
        log_FileFuncLine(f"defaults_by_var = {defaults_by_var}")
        log_FileFuncLine(f"scalar_vars = {scalar_vars}")

    if not scalar_vars:
        return clause  # return when no variable found
    yyyymmdd = get_first_by_key([dict1, opt], 'YYYYMMDD')
    dict2 = {}  # this is a local dict to avoid polluting caller's dict

    if yyyymmdd:
        if m := re.match(r"^(\d{4})(\d{2})(\d{2})$", yyyymmdd):
            yyyy, mm, dd = m.groups()
            dict2['yyyymmdd'] = yyyymmdd
            dict2['yyyy'] = yyyy
            dict2['mm'] = mm
            dict2['dd'] = dd
        else:
            raise Exception(f"YYYYMMDD='{yyyymmdd}' is in bad format")

    old_clause = clause
    idx_by_var = {}  # this is handle dup var because dup var is allowed.
    for var in scalar_vars:
        if var in idx_by_var:
            idx_by_var[var] += 1
        else:
            idx_by_var[var] = 0
        idx = idx_by_var[var]

        combined_dict = {**dict1, **dict2, **opt}
        if (value := get_value_by_key_case_insensitive(
                combined_dict, var, default=None)) is None:
            if verbose > 1:
                log_FileFuncLine(
                    f"var={var} is not in combined_dict={combined_dict}. checking default")
            if (default := defaults_by_var[var][idx]):
                # default is always defined, even if it is ''. but '' will be treated as False
                value = default
            else:
                if verbose:
                    log_FileFuncLine(
                        f"var={var} default is undefined. not resolving {var}")
                continue

        if value is None:
            continue
        # don't do global replacement because dup var may have different default.
        # re.sub(pattern, replacement, string, count, flags)
        # replacement must be a string. use f'{var}' to convert to string.
        # count=0 means replace all matches. default is 0.
        # count=1 means only replace the 1st match
        verbose > 1 and log_FileFuncLine(f"var={var} value={value}")

        # convert value to string
        # escape \ to \\, otherwise re.sub() will complain. eg
        #    change C:\Users\william to C:\\Users\\william
        if "\\" in f'{value}':
            value = f'{value}'.replace("\\", "\\\\")
            log_FileFuncLine(f"escaped \\ to \\\\ result in: {value}")
        clause = re.sub(r"\{\{" + var + r"(=.{0,200}?)?\}\}",
                        f'{value}',
                        clause,
                        count=1,  # only replace the 1st match
                        flags=re.IGNORECASE | re.MULTILINE)
        verbose and print(f"replaced #{idx} {{{var}}} with '{value}'")

    if clause == old_clause:
        return clause  # return when nothing can be resolved.

    # use the following to guard against deadloop
    level = opt.get("level", 0) + 1
    max_level = 10
    if level >= max_level:
        raise Exception(
            f"max_level={max_level} reached when trying to resolve clause={clause}. use verbose mode to debug")

    if opt:
        opt2 = {**opt}
        opt2['level'] = level
    else:
        opt2 = {'level': level}
    # print(f"opt2 = {opt2}")

    # recursive call
    clause = resolve_scalar_var_in_string(clause, dict1, **opt2)

    return clause


def switch_quotes(string1: str, outer: Literal['switch', 'double', 'single']):
    '''
    example
    because in windows cmd.exe, only double quotes can group.
    therefore, we need to change a command arg from
        'xpath=//*[@id="prime"]' 
    to
        "xpath=//*[@id='prime']"
    '''

    need_switch = False
    if outer == 'switch':
        # toggle between single and double quotes
        need_switch = True
    elif outer == 'double' or outer == 'single':
        if m := re.search(r"^.*?(['\"])", string1, re.MULTILINE):
            quote = m.group(1)
            if (quote == "'" and outer == 'single') or (quote == '"' and outer == 'double'):
                log_FileFuncLine(
                    f'current outer quote={quote} matches expected outer quote={outer}')
            else:
                need_switch = True
        else:
            log_FileFuncLine(f"no quote found in string1={string1}")
            need_switch = False
    else:
        raise Exception(
            f"unsupported outer={outer}. must be 'switch', 'double' or 'single'")

    if need_switch:
        pass
        # switch between tow chars: ' and "
        string2 = string1.translate(str.maketrans({"'": '"', '"': "'"}))

    else:
        string2 = string1
    return string2


def main():
    tests = [
        ('simple {{v1}} and {{v2}} and {{v3=abc}}',
         {'v1': 'hello', 'v2': 1}, 0),
        ('''multi-line {{v1}}
          and {{v2}}
          and {{v3=abc}}
         ''',  # this is a multi-line clause
         {'v1': 'hello', 'v2': 1}, 0),
        ('''dups {{v1}}
            and {{v2=2}}
            and {{v2=3}}
            and {{v3=abc}}
            and {{v3=def}}
          ''',
            {'v1': 'hello', 'v2': 1}, 0),
    ]
    for (clause, dict1, verbose) in tests:
        print('')
        print('----------------------------------------')
        print(f"clause = {clause}, dict1 = {pformat(dict1)}")
        print(
            f"resolved clause = {resolve_scalar_var_in_string(clause, dict1, verbose=verbose)}")

    def test_codes():
        switch_quotes('''
                      'xpath=//*[@id="prime1"]' 'xpath=//*[@id="prime2"]'
                      ''', 'switch')
        switch_quotes('''
                        "xpath=//*[@id='prime1']" "xpath=//*[@id='prime2']"
                        ''', 'switch')
        switch_quotes('''
                        'xpath=//*[@id="prime1"]' 'xpath=//*[@id="prime2"]'
                        ''', 'double')
        switch_quotes('''
                        'xpath=//*[@id="prime1"]' 'xpath=//*[@id="prime2"]'
                        ''', 'single')

        # we escape {{var}} in f"", double up
        resolve_scalar_var_in_string(f"{{{{prog}}}} is {1+1}", {'prog': 2})

    from tpsup.testtools import test_lines
    test_lines(test_codes)


if __name__ == '__main__':
    main()
