#!/usr/bin/env python3

from datetime import date

d1 = date(int('2025'), int('11'), int('25'))
d2 = date.today()

print(d1 - d2)
