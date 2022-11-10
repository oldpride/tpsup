#!/usr/bin/env python3

b=100

def temp(a):
    return a+1

plus1=temp

print(f'plus1={plus1(b)}')

def temp(a):
    return a+2

plus2=temp

print(f'plus2={plus2(b)}')
print(f'plus1={plus1(b)}')