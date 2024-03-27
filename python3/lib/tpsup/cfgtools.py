import os
from pprint import pformat
import re
from typing import Union


def check_syntax(node: dict,
                 syntax: dict,
                 path: str = '/',

                 # if 'fatal' is True, raise exception when error.
                 # true 'fatal' should be used only on top level call.
                 # therefore, we don't need to pass it down.
                 fatal: bool = False,
                 **opt):
    # recursively walk through hash and build each hash node's path.
    error = 0
    checked = ""
    message = ""
    matched = ""

    node_type = type(node)
    if node_type == dict:
        result = check_syntax_1_node(node, syntax, path, **opt)
        error += result['error']
        checked += result['checked']
        message += result['message']
        matched += result['matched']

        for k in node.keys():
            # print(f"{path}{k}/")
            result = check_syntax(node[k], syntax, f'{path}{k}/', **opt)
            error += result['error']
            checked += result['checked']
            message += result['message']
            matched += result['matched']
    elif node_type == list:
        for i in range(len(node)):
            print(f"{path}{i}/")
            result = check_syntax(node[i], syntax, f'{path}{i}/', **opt)
            error += result['error']
            checked += result['checked']
            message += result['message']
            matched += result['matched']
    else:
        # do nothing for other types.
        pass

    if fatal:
        if error > 0:
            raise RuntimeError(f"error={error} message={message}")
        if checked == "":
            raise RuntimeError(f"nothing was checked.")
        if matched == "":
            raise RuntimeError(f"nothing was matched.")

    return {'error': error, 'message': message, 'checked': checked, 'matched': matched}


def check_syntax_1_node(node: dict, syntax: dict, path: str, **opt):
    error = 0
    checked = ""
    message = ""
    matched = ""
    node_type = type(node)

    if node_type != dict:
        raise RuntimeError(f"node_type={node_type} is not dict. should never be here. node={pformat(node)}")

    for p in syntax.keys():
        if re.search(p, path):
            node_syntax = syntax[p]
            matched += f"pattern={p} matched path={path}\n"

            # print(f"path={path} pattern={p} node_syntax={pformat(node_syntax)}")

            result = check_syntax_1_node_1_syntax(node, node_syntax, path)
            error += result['error']
            checked += result['checked']
            message += result['message']

    return {'error': error, 'message': message, 'checked': checked, 'matched': matched}


def check_syntax_1_node_1_syntax(node: dict, node_syntax: dict, path: str, **opt):
    error = 0
    checked = ""
    message = ""

    # this function doesn't match patterns, so no need to return matched
    # matched = ""

    node_type = type(node)
    if node_type != dict:
        raise RuntimeError(f"node_type={node_type} is not dict. should never be here. node={pformat(node)}")

    for k in node.keys():
        checked += f"path={path} key={k}\n"
        v = node[k]

        if k not in node_syntax.keys():
            message += f"{path} key={k} is not allowed\n"
            error += 1
            continue

        expected_type = node_syntax[k].get('type', None)
        type_of_expected_type = type(expected_type)
        actual_type = type(v)

        if type_of_expected_type == list:
            if actual_type not in expected_type:
                message += f"{path} key={k} type mismatch: expected={expected_type} vs actual={actual_type}\n"
                error += 1
                continue
        elif type_of_expected_type == str:
            if expected_type is not None:
                if expected_type != actual_type:
                    message += f"{path} key={k} type mismatch: expected={expected_type} vs actual={actual_type}\n"
                    error += 1
                    continue
        else:
            raise RuntimeError(f"expected_type={expected_type} should be either list or str")

        pattern = node_syntax[k].get('pattern', None)
        if pattern is not None:
            if not re.match(pattern, f"{v}"):
                message += f"{path} key={k} value={v} not matching expected pattern\n"
                error += 1
                continue

    for k in node_syntax.keys():
        checked += f"path={path} required key={k}\n"
        v = node_syntax[k]
        required = v.get('required', False)
        if required and k not in node:
            message += f"{path} required key={k} is missing\n"
            error += 1
            continue

    return {'error': error, 'message': message, 'checked': checked}


def source_python_string_to_dict(py_string: str, varnames: Union[list[str], str]):
    # tpsup.batch does use this function to source cfg code because
    # tpsup.batch needs the cfg code in it own namespace.
    # this function source the code into tpsup.expression namespace.
    import tpsup.expression
    tpsup.expression.run_code(py_string)
    # our_cfg2 = tpsup.expression.our_cfg
    # use get attribute to avoid pylint warning
    # our_cfg2 = getattr(tpsup.expression, 'our_cfg')

    if type(varnames) == str:
        varname = varnames
        return getattr(tpsup.expression, varname)
    elif type(varnames) == list:
        ret = {}
        for varname in varnames:
            var = getattr(tpsup.expression, varname)
            ret[varname] = var
        return ret
    else:
        raise RuntimeError(f"varnames={varnames} should be either str or list")


def source_python_file_to_dict(py_file: str, varnames: list[str]):
    # read the file into a string
    with open(py_file) as f:
        py_string = f.read()
    return source_python_string_to_dict(py_string, varnames)


def main():
    # load test cfg file cfgtools_test_cfg.py in the same directory
    module_dir = os.path.dirname(__file__)
    test_cfg_file = os.path.join(module_dir, 'cfgtools_test_cfg.py')
    test_syntax_file = os.path.join(module_dir, 'cfgtools_test_syntax.py')
    # # read the file into a string
    # global our_cfg  # exec will populate this global variable
    # test_cfg_string = None
    # with open(test_cfg_file) as f:
    #     test_cfg_string = f.read()
    #     # print(f"test_cfg_string={test_cfg_string}")
    # from tpsup.exectools import exec_into_globals
    # exec_into_globals(test_cfg_string, globals(), locals())
    # print(f"our_cfg={pformat(our_cfg)}")

    # import tpsup.expression
    # tpsup.expression.compile_code(test_cfg_string, function_wrap=False)
    # # our_cfg2 = tpsup.expression.our_cfg
    # # use get attribute to avoid pylint warning
    # our_cfg2 = getattr(tpsup.expression, 'our_cfg')
    # print(f"our_cfg2={pformat(our_cfg2)}")

    our_cfg = source_python_file_to_dict(test_cfg_file, 'our_cfg')
    print(f"our_cfg={pformat(our_cfg)}")
    our_syntax = source_python_file_to_dict(test_syntax_file, 'our_syntax')
    print(f"our_syntax={pformat(our_syntax)}")

    check_result = check_syntax(our_cfg, our_syntax, fatal=True)
    print(f"check_result={pformat(check_result)}")


# call main() if this script is run standalone
if __name__ == '__main__':
    main()
