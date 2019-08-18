#!/usr/bin/env python3

# https://stackoverflow.com/questions/2776829/difference-between-pythons-generators-and-iterators
#
# Most often, a generator (sometimes, for sufficiently simple needs, a generator expression) is sufficient,
# and it's simpler to code because state maintenance (within reasonable limits) is basically "done for you" by the
# frame getting suspended and resumed.
#
# You may want to use a custom iterator, rather than a generator, when you need a class with somewhat complex
# state-maintaining behavior, or want to expose other methods besides next (and __iter__ and __init__).

import collections, types

print(issubclass(types.GeneratorType, collections.Iterator))


# True
def a_function():
    """just a function definition with yield in it"""
    yield


print(type(a_function))

# <class 'function'>
a_generator = a_function()  # when called
print(type(a_generator))  # returns a generator
# <class 'generator'>

# And a generator, again, is an Iterator:

print(isinstance(a_generator, collections.Iterator))
# True
