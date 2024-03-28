
from pprint import pformat


_exist = {}  # keep track of the existence of variables
# keep track of fix-protocol variables
# fix protocal uses number as key; therefore, we need to add a prefix to the key.
# 35 can be a variable name, but fix['35'] can.
fix = {}


def export_var(ref: dict,
               ExpPrefix=None,  # prefix the exported variables
               RESET=False,  # whether to clear the existing variables
               FIX=False,  # fix protocol
               verbose=False):

    # we use this function to populate the global variables

    global _exist
    global fix
    prefix = ExpPrefix
    if RESET:
        if prefix:
            if prefix in globals():
                var = globals()[prefix]
                if isinstance(var, dict):
                    # how to clear a dict ?
                    # https://stackoverflow.com/questions/369898
                    # var = {}
                    var.clear()
        elif FIX:
            fix.clear()
        else:
            _exist.clear()

    if prefix:
        if prefix not in globals():
            globals()[prefix] = {}
        for k in ref:
            if isinstance(ref[k], dict):
                # only support 2 levels of nesting
                for k2 in ref[k]:
                    globals()[prefix][k][k2] = ref[k][k2]
            else:
                globals()[prefix][k] = ref[k]
    elif FIX:
        for k in ref:
            if isinstance(ref[k], dict):
                for k2 in ref[k]:
                    fix[k][k2] = ref[k][k2]
            else:
                fix[k] = ref[k]
    else:
        for k in ref:
            if isinstance(ref[k], dict):
                if k not in globals():
                    globals()[k] = {}
                for k2 in ref[k]:
                    globals()[k][k2] = ref[k][k2]
                    _exist[k] = 1
            else:
                globals()[k] = ref[k]
                _exist[k] = 1


def dump_var(DumpFH=None, ExpPrefix=None, FIX=False):
    prefix = ExpPrefix
    if prefix:
        if prefix in globals():
            print(f"\n{prefix} =\n", file=DumpFH)
            print(f"{pformat(globals()[prefix])}", file=DumpFH)
        else:
            print(f"\n{prefix} is not defined", file=DumpFH)
    elif FIX:
        print("\n%fix =\n", file=DumpFH)
        print(f"{pformat(fix)}", file=DumpFH)
    else:
        print("\nvars =\n", file=DumpFH)
        for k in sorted(_exist):
            print(f"{k} => {pformat(globals()[k])}", file=DumpFH)


compiled_by_source = {}


def run_code(source: str,
             function_wrap=False,
             is_exp=False,  # whether the source is an expression, exp needs return statement
             **opt):

    verbose = opt.get('verbose', False)

    if source in compiled_by_source:
        return compiled_by_source[source]

    if function_wrap:
        source2 = 'def f():\n'

        if is_exp:
            # this is an expression
            # we need to add a return statement
            source2 += f"    return {source}\n"
        else:
            source2 += f"    {source}\n"
    else:
        source2 = source

    if verbose:
        print(f"compile source=\n'\n{source2}'")

    try:
        compiled = compile(source2, '<string>', 'exec')
    except Exception as e:
        raise Exception(f"failed to compile source='{source2}': {e}")

    ret = None
    try:
        ret = exec(compiled, globals())
    except Exception as e:
        raise Exception(f"failed to execute compiled source='{source2}': {e}")

    if verbose:
        print(f'globals={pformat(globals())}')

    if function_wrap:
        compiled_by_source[source] = globals()['f']
        # compiled_by_source[source] = f # this will work too! but vscode will complain.
        return compiled_by_source[source]
    else:
        return ret


def compile_exp(source: str, **opt):
    return run_code(source, function_wrap=True, **opt)


def main():
    def test_codes():
        export_var({'a': 1, 'b': 2, 'c': 3}) == None
        # dump_var()
        a+b == 3
        export_var({'a': 4, 'd': 5}, RESET=True) == None
        # dump_var()
        a+d == 9

        export_var({'a': 7, 'b': 8, 'c': 9}, ExpPrefix='tian', RESET=True) == None
        # dump_var(ExpPrefix='tian')
        tian['a']+tian['b'] == 15

        compile_exp('a+d', is_exp=True)() == 9

        # test string expression
        compile_exp('f"a={a}, d={d}"', is_exp=True,)() == 'a=4, d=5'

        # no (), ie, no execution of function here!!! only run code.
        run_code('myvar=a+d') == None
        myvar == 9

    from tpsup.testtools import test_lines
    test_lines(test_codes)
    # test_codes()


if __name__ == '__main__':
    main()
