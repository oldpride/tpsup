#!/usr/bin/env python3

import datetime

# get days between two dates
def get_days_between_dates(date1, date2):
    return (date2 - date1).days + 1

print(get_days_between_dates(datetime.date(2018, 1, 1), datetime.date(2018, 1, 3)))