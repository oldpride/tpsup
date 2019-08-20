import cx_Oracle
from pprint import pprint,pformat
import os
import sys
from os.path import expanduser
from tpsup.csv import query_csv
from tpsup.util import tpeng_unlock
import re

def unlock_conn(nickname2, **opt):
    if 'connfile' in opt and opt['connfile']:
        connfile = opt['connfile']
    else:
        # home-directory-in-python
        home = expanduser("~")
        connfile = home + "/.tpsup/conn.csv"

    ret = {}

    if not os.path.exists(connfile):
        print >>sys.stderr, 'connection file ' + connfile + ' not found'
        return ret

    opt2 = {}
    opt2['file'] = connfile

    struct = {}
    struct = query_csv(**opt2)

    if 'columns' not in struct:
        print >>sys.stderr, 'failed to read ' + connfile
        return ret

    rows = struct['array']
    columns = struct['columns']
    delimiter = struct['delimiter']

    if 'nickname' not in columns:
        print >>sys.stderr, 'failed to parse ' + connfile
        return ret

    found_row = {}

    for row in rows:
        if nickname2 == row['nickname']:
            found_row = row
            break

    if len(found_row) > 0:
        dbiString = found_row['string']
        login = found_row['login']
        locked_password = found_row['password']
    else:
        print >>sys.stderr, 'nickname=', nickname2, "doesn't exist in", connfile
        return ret

    # https://stackoverflow.com/questions/2554185/match-groups-in-python
    m0 = re.match("^dbi:(.+?):(.+)", dbiString)
    if m0:
        ret["database"] = m0.group(1)
        pairs = m0.group(2)

        for pair in (pairs.split(";")):
            m1 = re.match("^(.+?)=(.+)", pair)
            if ml:
                key = ml.group(1)
                val = ml.group(2)
                ret[key] = val

    ret["string"] = dbiString
    ret["login"]  = login
    ret["locked_password"] = locked_password
    ret["unlocked_password"] = tpeng_unlock(locked_password, None)

    return ret

dbh_by_nickname = {}
current_dbh = None

def get_dbh(**opt) :
    # https://stackoverflow.com/questions/1977362/how-to-create-module-wide-variables-in-python

    global dbh_by_nickname
    global current_dbh

    if 'nickname' in opt:
        nickname = opt['nickname']

        if nickname in dbh_by_nickname:
            dbh = dbh_by_nickname[nickname]
            current_dbh = dbh
            return dbh

        info = unlock_conn(nickname, **opt)

        if 'sid' in info:
            dsn_tns = cx_Oracle.makedsn(info['host'], info['port'], info['sid'])

            dbh = cx_Oracle.connect(info['login'], info['unlocked_password'], dsn_tns)
        elif 'service_name' in info:
            # use service name
            # https://stackoverflow.com/questions/51486739/how-to-connect-
            # to-an-oracle-database-using-cx-oracle-with-service-name-and-login
            # con = cx_Oracle.connect('username/password@host_name:port/
            # service_name')

            string = info['login'] + '/' + info['unlocked_password'] + '@'\
                    + info['host'] + ':' + info['port'] + '/' + info['service_name']
            dbh = cx_Oracle.connect(string)

            dbh_by_nickname[nickname] = dbh
            current_dbh = dbh
        elif current_dbh :
            dbh = current_dbh

        return dbh

def run_sql(sql, **opt):
    global dbh_by_nickname
    global current_dbh

    ret = {}

    dbh = get_dbh(**opt)

    if not dbh:
        return ret

    cursor = dbh.cursor()

    cursor.parse(sq1)

    cursor.execute(sql)

    #rows = []
    #for row in cursor:
    # rows.append(row)

    ret['columns'] = [row[0] for row in cursor.description]
    ret['rows'] = cursor.fetchall()

    if 'output' in opt and opt['output']:
        output = opt['output']

        if output == '-':
            ofo = sys.stdout
        else:
            ofo = open(output, 'w')

        if 'odelimiter' in opt:
            odelimiter = opt['odelimiter']
        else:
            odelimiter = ','

        ofo.write(odelimiter.join(ret['columns']) + "\n")

        for r in ret['rows']:
            # https://stackoverflow.com/questions/111192 85/string-joining-
            # from- iterable-containing-strings-and-nonetype-undefined
            ofo.write(odelimiter.join(item or '' for item in r) + "\n")

        ofo.close()

    return ret
