import datetime
import datetime
import os
from pprint import pformat
import re
import csv
import datetime
import sys

from tpsup.searchtools import binary_search_match

# Date and time objects may be categorized as “aware” or “naive” depending on whether or not they include timezone information.
#     Objects of the "date" type are always naive.
#     An object of type "time" or "datetime" may be aware or naive.
#
# A datetime object d is aware if both of the following hold:
#     d.tzinfo is not None
#     d.tzinfo.utcoffset(d) does not return None
# Otherwise, d is naive.
#
# A time object t is aware if both of the following hold:
#     t.tzinfo is not None
#     t.tzinfo.utcoffset(None) does not return None.
# Otherwise, t is naive.
# Subclass relationships:
# object
#     timedelta
#     tzinfo
#         timezone
#     time
#     date
#         datetime


tzinfo = None


def get_timezone():
    global tzinfo
    if tzinfo:
        return tzinfo
    else:
        tzinfo = datetime.datetime.now().astimezone().tzinfo
    return tzinfo


def get_date(**opt):
    if yyyymmdd := opt.get('yyyymmdd', None):
        yyyy, mm, dd = yyyymmdd[:4], yyyymmdd[4:6], yyyymmdd[6:8]
        dt = datetime.datetime(year=int(yyyy), month=int(mm), day=int(dd), tzinfo=get_timezone())
    else:
        dt = datetime.datetime.now(tz=get_timezone())
    r = {}
    r['yyyy'] = dt.strftime('%Y')
    r['mm'] = dt.strftime('%m')
    r['dd'] = dt.strftime('%d')
    r['HH'] = dt.strftime('%H')
    r['MM'] = dt.strftime('%M')
    r['SS'] = dt.strftime('%S')
    r['offset'] = dt.strftime('%z')
    r['WD'] = dt.strftime('%w')
    r['datetime'] = dt

    return r


def get_yyyymmdd(**opt):
    date = get_date(**opt)
    return f"{date['yyyy']}{date['mm']}{date['dd']}"


def get_yyyymmdd_by_yyyymmdd_offset(yyyymmdd1, offset, **opt):
    # from tpsup.cmdtools import run_cmd
    # yyyymmdd2 = run_cmd(f'date -d "{yyyymmdd1} {offset} day" "+%Y%m%d"', is_bash=True)['stdout'].strip()
    yyyy, mm, dd = yyyymmdd1[:4], yyyymmdd1[4:6], yyyymmdd1[6:8]
    date1 = datetime.datetime(year=int(yyyy), month=int(mm), day=int(dd))
    date2 = date1 + datetime.timedelta(days=offset)
    yyyymmdd2 = date2.strftime("%Y%m%d")
    return yyyymmdd2


def get_timezone_offset():
    local_sec = datetime.datetime.now().timestamp()
    t = datetime.datetime.utcfromtimestamp(local_sec)
    gmt_offset_in_seconds = (t - datetime.datetime.fromtimestamp(local_sec)).total_seconds()
    gmt_offset_in_hours = gmt_offset_in_seconds / 3600
    return gmt_offset_in_hours


exists_by_exch_holiday = {}
holidays_by_exch = {}


def parse_holiday_csv(exch, HolidayRef: dict = None, HolidaysCsv: str = None, **opt):

    if HolidayRef:
        exists_by_exch_holiday[exch] = HolidayRef
        return exists_by_exch_holiday[exch]

    if exists_by_exch_holiday.get(exch, None):
        return exists_by_exch_holiday[exch]

    if not HolidaysCsv:
        perllib_dir = get_perllib_dir()
        HolidaysCsv = os.path.join(perllib_dir, 'DATE_holidays.csv')

    if not os.path.isfile(HolidaysCsv):
        raise FileNotFoundError(f"{HolidaysCsv} is not found")

    ref = {}

    with open(HolidaysCsv, 'r') as fh:
        row_count = 0
        while line := fh.readline():
            row_count += 1

            if line.startswith(f"{exch},"):
                # name,days
                # NYSE,20200101 20200120 20200217 ...
                row = line.strip().split(',')
                holidays = row[1].split()

                yyyymmdd_pattern = r'\d{8}'
                yyyymmdd_compiled = re.compile(yyyymmdd_pattern)

                item_count = 0
                last_holiday = None

                for yyyymmdd in holidays:
                    item_count += 1

                    if re.match(yyyymmdd_compiled, yyyymmdd):
                        if last_holiday and yyyymmdd <= last_holiday:
                            raise ValueError(
                                f"{HolidaysCsv} row {row_count} item {item_count} '{yyyymmdd}' <= last one '{last_holiday}', out of order")
                        last_holiday = yyyymmdd
                        ref[yyyymmdd] = 1
                    else:
                        raise ValueError(f"{HolidaysCsv} row {row_count} item {item_count} '{yyyymmdd}' bad format")

                break
    if not ref:
        raise ValueError(f"no holiday info found for {exch} in {HolidaysCsv}")

    holidays_by_exch[exch] = holidays
    exists_by_exch_holiday[exch] = ref

    return exists_by_exch_holiday[exch]


def is_holiday(exch, yyyymmdd, **opt):
    parse_holiday_csv(exch, **opt)
    return exists_by_exch_holiday[exch].get(yyyymmdd, None)


def yyyymmdd_to_DayOfWeek(yyyymmdd: str, **opt):
    date = get_date(yyyymmdd=yyyymmdd)
    return date['WD']


yyyymmddHHMMSS_pattern = r'(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})'
yyyymmddHHMMSS_compiled = None


def yyyymmddHHMMSS_to_epoc(yyyymmddHHMMSS, fromUTC=False, **opt):
    # convert time to seconds from epoch

    settings = {}
    if fromUTC:
        settings['tzinfo'] = datetime.timezone.utc

    if type(yyyymmddHHMMSS) == list:
        if len(yyyymmddHHMMSS) != 6:
            print(f"bad format of yyyymmddHHMMSS list={pformat(yyyymmddHHMMSS)}", file=sys.stderr)
            raise ValueError("List size must be 6")

        dt = datetime.datetime(*yyyymmddHHMMSS, **settings)

    else:
        global yyyymmddHHMMSS_compiled
        if yyyymmddHHMMSS_compiled == None:
            yyyymmddHHMMSS_compiled = re.compile(yyyymmddHHMMSS_pattern)

        if m := re.match(yyyymmddHHMMSS_compiled, yyyymmddHHMMSS):
            yyyy, mm, dd, HH, MM, SS = m.groups()

            dt = datetime.datetime(int(yyyy), int(mm), int(dd), int(HH), int(MM), int(SS), **settings)
        else:
            raise ValueError(f"yyyymmddHHMMSS='{yyyymmddHHMMSS}', bad format")

    seconds = dt.timestamp()
    return seconds


def epoc_to_yyyymmddHHMMSS(epoc, toUTC=False, **opt):
    if toUTC:
        dt = datetime.datetime.utcfromtimestamp(epoc)
    else:
        dt = datetime.datetime.fromtimestamp(epoc)
    # print(pformat(dt))
    return dt.strftime('%Y%m%d%H%M%S')
    # dt = datetime.datetime.fromtimestamp(epoc)
    # if toUTC:
    #     return dt.astimezone(datetime.timezone.utc).strftime('%Y%m%d%H%M%S')
    # else:
    #     return dt.strftime('%Y%m%d%H%M%S')


def get_yyyymmddHHMMSS(**opt):
    now_sec = datetime.datetime.now().timestamp()
    return epoc_to_yyyymmddHHMMSS(now_sec, **opt)


perllib_dir = None


def get_perllib_dir():
    global perllib_dir
    if not perllib_dir:
        directory = os.path.dirname(os.path.abspath(__file__))
        perllib_dir = os.path.join(directory, '../../../lib/perl/TPSUP')
    return perllib_dir


weekdays = None


def get_weekdays():
    global weekdays
    if not weekdays:
        directory = get_perllib_dir()
        file = os.path.join(directory, 'DATE_weekdays.txt')
        with open(file, 'r') as fh:
            string = fh.read()
            weekdays = string.split()
            weekdays.pop()  # remove the last empty element
    return weekdays


tradeday_by_exch_begin_offset = {}


def get_tradeday_by_exch_begin_offset(exch, begin, offset,
                                      IgnoreHoliday=False,
                                      OnWeekend=None,
                                      # next, prev. 'next' means if the begin is on weekend,
                                      # then the next trade day is the first trade day
                                      **opt):
    global tradeday_by_exch_begin_offset

    verbose = opt.get('verbose', 0)

    if exch not in tradeday_by_exch_begin_offset:
        tradeday_by_exch_begin_offset[exch] = {}

    if begin not in tradeday_by_exch_begin_offset[exch]:
        tradeday_by_exch_begin_offset[exch][begin] = {}

    if offset in tradeday_by_exch_begin_offset[exch][begin]:
        return tradeday_by_exch_begin_offset[exch][begin][offset]

    is_holiday = {}

    # exch == 'WeekDay' is a special case, which means ignore holiday
    if IgnoreHoliday or exch == 'WeekDay':
        IgnoreHoliday = True
    else:
        is_holiday = parse_holiday_csv(exch, opt=opt)

    weekdays = get_weekdays()

    # if the binary search falls between two connective trade days, eg, on weekends
    InBetween = 'low'
    if OnWeekend and OnWeekend == 'next':
        InBetween = 'high'

    begin_weekday_pos = binary_search_match(weekdays, begin, 'string',
                                            InBetween=InBetween, OutBound='Error')
    verbose and print(f"begin_weekday={weekdays[begin_weekday_pos]}", file=sys.stderr)

    if IgnoreHoliday:
        # without taking holiday into account, we basically return a weekday
        return weekdays[begin_weekday_pos + offset]

    # we haven't considered holidays yet. now we need to do that

    # first make sure the begin_weekday is not a holiday
    begin_tradeday_pos = begin_weekday_pos

    while is_holiday.get(weekdays[begin_tradeday_pos]):
        if OnWeekend == 'next':
            begin_tradeday_pos += 1
        else:
            begin_tradeday_pos -= 1

    # tradeday is a non-holiday weekday
    begin_tradeday = weekdays[begin_tradeday_pos]
    verbose and print(f"begin_tradeday={begin_tradeday}", file=sys.stderr)

    if offset == 0:
        # we only cache offset from a tradeday, as offset from weekend and holiday
        # can be affected by OnWeekend flag
        tradeday_by_exch_begin_offset[exch][begin_tradeday][offset] = begin_tradeday
        return begin_tradeday
    else:
        new_pos = begin_tradeday_pos

        if offset > 0:
            for i in range(1, offset + 1):
                new_pos += 1
                while is_holiday.get(weekdays[new_pos], None):
                    new_pos += 1
        elif offset < 0:
            for i in range(-1, offset - 1, -1):
                new_pos -= 1
                while is_holiday.get(weekdays[new_pos], None):
                    new_pos -= 1

        new_tradeday = weekdays[new_pos]

        #  we only cache offset from a tradeday, as offset from weekend and holiday
        # can be affected by OnWeekend flag
        tradeday_by_exch_begin_offset[exch][begin_tradeday][offset] = new_tradeday
        return new_tradeday


def get_holidays_by_exch_begin_end(exch, begin, end, opt):
    parse_holiday_csv(exch, opt)

    if exch not in holidays_by_exch or not holidays_by_exch[exch]:
        raise Exception(f"no holiday information for exch={exch}")

    all_holidays = holidays_by_exch[exch]

    holidays = []
    begin_covered = False
    end_covered = False

    for d in all_holidays:
        if d >= end:
            end_covered = True

            if d == end:
                holidays.append(d)

            break

        if d >= begin:
            holidays.append(d)
            if d == begin:
                begin_covered = True
        else:
            begin_covered = True

    if not end_covered:
        print(f"end={end} exceeded upper range of '{exch}' holidays ({all_holidays[-1]})")

    if not begin_covered:
        print(f"begin={begin} exceeded lower range of '{exch}' holidays ({all_holidays[0]})")

    return holidays


def main():
    def test_codes():
        get_timezone()
        get_date()
        get_yyyymmdd()
        yyyymmdd_to_DayOfWeek(yyyymmdd=get_yyyymmdd())
        get_date(yyyymmdd='20200901')
        get_yyyymmdd_by_yyyymmdd_offset('20200901', -1) == '20200831'
        get_timezone_offset() in (4.0, 5.0)
        is_holiday('NYSE', '20240101') == 1
        yyyymmddHHMMSS_to_epoc('20200901120000')
        epoc_to_yyyymmddHHMMSS(1598976000)
        yyyymmddHHMMSS_to_epoc('20200901120000', fromUTC=True)
        epoc_to_yyyymmddHHMMSS(1598961600, toUTC=True)

        yyyymmddHHMMSS_to_epoc([2020, 9, 1, 12, 0, 59])
        yyyymmddHHMMSS_to_epoc([2020, 9, 1, 12, 0, 59], fromUTC=1)
        yyyymmddHHMMSS_to_epoc([2020, 9, 1, 12, 0, 59], fromUTC=1) - yyyymmddHHMMSS_to_epoc([2020, 9, 1, 12, 0, 59])

        get_yyyymmddHHMMSS()
        get_yyyymmddHHMMSS(toUTC=True)

        # 20200907, Monday, is a holiday, labor day
        get_tradeday_by_exch_begin_offset('NYSE', '20200901', 3, ) == '20200904'  # within the same week
        get_tradeday_by_exch_begin_offset('NYSE', '20200904', -3, ) == '20200901'
        get_tradeday_by_exch_begin_offset('NYSE', '20200901', 4, ) == '20200908'  # across the weekend and holiday
        get_tradeday_by_exch_begin_offset('NYSE', '20200908', -4, ) == '20200901'

        get_tradeday_by_exch_begin_offset('NYSE', '20200904', 0, ) == '20200904'  # 0 offset on a trade day
        get_tradeday_by_exch_begin_offset('NYSE', '20200905', 0, ) == '20200904'  # 0 offset on a weekend
        get_tradeday_by_exch_begin_offset('NYSE', '20200907', 0, ) == '20200904'  # 0 offset on a holiday

        get_tradeday_by_exch_begin_offset('NYSE', '20200905', 0, OnWeekend='next') == '20200908'
        get_tradeday_by_exch_begin_offset('NYSE', '20200907', 0, OnWeekend='next') == '20200908'

        get_tradeday_by_exch_begin_offset('NYSE', '20200907', 1) == '20200908'
        get_tradeday_by_exch_begin_offset('NYSE', '20200907', 1, OnWeekend='next') == '20200908'

    import tpsup.exectools
    tpsup.exectools.test_lines(test_codes, globals(), locals())


if __name__ == "__main__":
    main()
