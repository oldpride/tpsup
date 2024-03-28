
python stack frame vs namespace
    https://stackoverflow.com/questions/71646713
    Scope (namespace) is just one of the LEGB: Local, Enclosing, Global and Built-in.
    They are namespaces that Python uses to look up names. 
    LEGB is the order in which that lookup is performed, 
        first the local scope is checked for a names, 
        then the enclosing scope, 
        then global, 
        built-in 
        and if it's never found, you end up with an exception.

    This ordering is the reason for 'shadowing': if you define something in local scope,
    it shadows global, because local scope is checked before global scope. 
    The definition doesn't overwrite the previous one, it shadows it. 
    
    If you redefine a variable in the same scope, it overwrites the previous variable
    and you can't get it back.

    A stack frame is created every time a function is called (and
    a global frame every time a module is loaded). 
    
    The stack frame handles the local variables for the function. 
    Every time another function is called, a new stack frame is created, creating a new local scope. 
    This allows every call to a function to have its own set of local variables, without access to
    the local scope of previous calls. Every time a function returns, that stack frame is destroyed,
    and you end back up in the previous stack frame (so, it's a 'stack').

    So 'stack frame' is related to 'scope' in that the local scope is on the top-most stack frame. 
    A stack frame contains the local scope for a function call, and a global frame contains the
    global scope for a module.

    Roughly speaking, "stack frame" is to "scope" as "instance" is to "class".

python's stack frame can be accessed through "inspect" module.
    https://docs.python.org/3/library/inspect.html
    
------------------------------------------------------------------------

exectools.py vs modtools.py vs expression.py

exectools.py
    exectools.py compiles code at run time.
    the caller need to pass the namespace, globals(), to the module; 
    so that when the compiled code is executed, it can access the caller's objects.
    eg, 
        test_code = ' 1+1 == 2'
        import tpsup.exectools
        tpsup.exectools.eval_block(test_code, globals(), locals())
        # the last step pass the caller's namespace (all objects) to the module
    being able to access caller's objects is a double edge sword.
        it is dangerous because the module could pollute the caller's namespace.
        it is convenient because the module can access the caller's objects.
    for this reason, we mainly use it for testing purpose, 
        only in the caller module's main() function.

modtools.py
    modtools.py compiles code also compiles code at run time.
    it dynamically creates a module (dynamic dedicate namespace).
    but the caller does not pass the namespace, globals(), to the module. 
    Therefore, the module cannot access caller's objects.
    If the new module needs the caller's objects (namespace), the caller has
    to pass caller's objects using function parameters.
    eg, 

        from modtools import compile_code
        a = 1
        compiled = compile_code(code)
        compiled(a)  # pass caller's objects to the compiled code
    not being able to access caller's objects make modtools safe.
        because the module cannot pollute the caller's namespace.
        
expression.py
    expression.py compiles code at run time.
    expression.py is different from modtools.py in that it doesn't create a module.
    expression.py is different from exectools.py in that it doesn't access caller's namespace.

    expression.py is similar to tpsup/lib/TPSUP/Expression.pm.
    it provides a static dedicate namespace to the compiled code.
    the caller needs to populate this namespace 
       (or pass caller's objects using function parameters).
    the advantage of keeping the objects (copied from caller) and the compiled code
       in the same namespace makes the code simpler and more readable.
       f"{yyyy} {mm} {dd}" is more readable than f"{r['yyyy']} {r['mm']} {r['dd']}"
    example,
        # populate the namespace with caller's objects (selectively)
        tpsup.expression.export_var(r)   
        compiled = tpsup.expression.compile_code(template, is_exp=True, **opt)
        # no need to pass caller's objects to the compiled code
        converted = compiled()           

which to choose?
    if you need to access caller's objects, use exectools.py. this is why
        tpsup.testtools uses exectools.py.
    if you need to access caller's objects, but you don't want to pollute
        caller's namespace, use expression.py or modtools.py
        between expression.py and modtools.py, 
            - if you don't want multiple calls interfere with each other, use modtools.py
            because modtools.py creates a dedicate namespace for each compiled code.
            - if you do want multiple calls to share the same namespace, use expression.py
            because expression.py uses the same namespace for all compiled code.

python vs perl
    our python code had 3 different modules to compile code at run time.
    our perl code had only one module to compile code at run time. Expression.pm.

    the reason is perl's eval is more powerful than python3's eval.
    python2 eval was as powerful as perl's eval.

--------------------------------------------------------------------------------------------------
2024/02/18 break dependency loop, or circular import
a.py
  import b
  ...
  def a_f:
    b.b_f

b.py
  import a
  ...
  def b_f:
    a.a_f

when i run either of the py file, I will get "partitally imported..."
to fix it
a.py
  ...
  def a_f:
    import b
    b.b_f

b.py
  ...
  def b_f:
    import a
    a.a_f

2024/02/20 i break big module into smaller pieces.
new scheme
   named the basic modules to *basic.py, eg, logbasic.py.
      these basic modules should not import other tpsup.* modules or at least with extra care.

--------------------------------------------------------------------------
2024/03/19 removed all re.compile cache because python already caches it.
