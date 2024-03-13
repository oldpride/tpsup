exectools.py vs modtools.py vs expression.py

exectools.py
    exectools.py compiles code at run time.
    the caller need to pass the namespace, globals(), to the module; 
    so that when the compiled code is executed, it can access the caller's objects.
    eg, 
        test_code = ' 1+1 == 2'
        import tpsup.exectools
        tpsup.exectools.eval_block(test_code, globals(), locals())
    being able to access caller's objects is a double edge sword.
        it is dangerous because the module could pollute the caller's namespace.
        it is convenient because the module can access the caller's objects.
    for this reason, we mainly use it for testing purpose, 
        only in the caller module's main() function.

modtools.py
    modtools.py compiles code also compiles code at run time.
    it dynamically creates a module. 
    but the caller does not need to pass the namespace, globals(), to the module. 
    Therefore, the module cannot access caller's objects.
    caller has to pass caller's objects using function parameters.
    eg, 

        from modtools import compile_code
        a = 1
        compiled = compile_code(code)
        compiled(a)
    not being able to access caller's objects make modtools safe.
        because the module cannot pollute the caller's namespace.
        
expression.py
    expression.py compiles code at run time.
    expression.py is different from modtools.py in that it doesn't create a module.
    expression.py is different from exectools.py in that it doesn't access caller's namespace.

    expression.py is similar to tpsup/lib/TPSUP/Expression.pm.
    it provides a dedicate namespace to the compiled code.
    the caller needs to populate this namespace 
       or pass caller's objects using function parameters.


