
#!/usr/bin/env python

# this is used to save cross-module variables
# https://stackoverflow.com/questions/142545/how-to-make-a-cross-module-variable
# "It is still possible to make an assignment to, say, g.x when x was not already defined in g, and a different module can then access g.x."
#

# this module should not avoided in general but it is useful when during
# exec() to pass variables as exec is a function so that it can only store
# variable in global scope

# use dir(module_name) to exam variable names

def test():
    a=1
