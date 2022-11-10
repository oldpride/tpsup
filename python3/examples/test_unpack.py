#!/usr/bin/env python

a = [1, 2]
x1, x2, x3, x4, *_ = a + [None] * 4

print(f'x1={x1}, x2={x2}, x3={x3}, x4={x4}')