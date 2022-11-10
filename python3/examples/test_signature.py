#!/usr/bin/env python3

import inspect
import io
import gzip

print('\nworks for python module\n')
print(inspect.signature(gzip.open))

print("\ndoesn't work for build-in module, eg, cython\n")
print(inspect.signature(io.BytesIO.__exit__))
