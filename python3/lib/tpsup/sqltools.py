# https://www.oracle.com/technetwork/prez-python-queries-101587.html

import cx_Oracle
from pprint import pprint, pformat
import os
import sys
from os.path import expanduser
import tpsup.csvtools
from tpsup.util import tpsup_unlock
import re


class Conn:
    def __init__(self, nickname: str, **opt):
        self.connfile = opt.get('connfile', expanduser("~") + "/.tpsup/conn.csv")
        self.error = None

        if not os.path.exists(connfile):
            raise RuntimeError(f'connection file {connfile} not found')

        opt['MatchExps'] = [f'r["nickname"] == "{nickname}"']

        dictlist = list(QueryCsv(connfile, **opt))

        if len(dictlist) == 0:
            raise RuntimeError(f"connection file {connfile} does not contain nickname = {nickname}")
        elif len(dictlist) > 1:
            raise RuntimeError(f'connection file {connfile} has multiple nickname = {nickname} defined')

        self.dbi_string = dictlist[0]['string']
        self.login = dictlist[0]['login']
        self.locked_password = dictlist[0]['password']
        self.parts = {}

        # https://stackoverflow.com/questions/2554185/match-groups-in-python
        m0 = re.match("^dbi:(.+?):(.+)", self.dbi_string)
        if m0:
            ret["database"] = m0.group(1)
            pairs = m0.group(2)

            for pair in (pairs.split(";")):
                key, value = pair.split("=", 1)
                self.parts[key] = value

        self.string = dbi_string
        self.login = login
        self.locked_password = locked_password
        self.unlocked_password = tpsup.util.tpsup_unlock(locked_password)


class TpDbh:
    def __init__(self, nickname: str, **opt):
        conn = Conn(nickname, **opt)
        self.conn = conn
        self.dbh = None

    def get_dbh(self):
        conn = self.conn
        parts = conn.parts

        if re.match("Oracle", conn.string):
            if 'sid' in parts:
                dsn_tns = cx_Oracle.makedsn(parts['host'], parts['port'], parts['sid'])
                self.dbh = cx_Oracle.connect(conn.login, conn.unlocked_password, dsn_tns)
            elif 'service_name' in parts:
                # use service name
                # https://stackoverflow.com/questions/51486739/how-to-connect-
                # to-an-oracle-database-using-cx-oracle-with-service-name-and-login
                # con = cx_Oracle.connect('username/password@host_name:port/
                # service_name')

                string = f'{conn.login}/{conn.unlocked_password}@{parts["host"]}:{parts["port"]}/{parts["service_name"]}'
                self.dbh = cx_Oracle.connect(string)
            else:
                raise RuntimeError(f"unsupported oracle dbi_string {conn.dbi_string}")
        else:
            raise RuntimeError(f"unknown database dbi_string {conn.dbi_string}")

        return self.dbh

    def __enter__(self):
        return self.get_dbh()

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.dbh:
            self.dbh.close()


class QueryResults:
    def __init__(self, sql, **opt):
        self.sql = sql
        self.opt = opt
        self.columns = None

    def iterator(self, sql):
        opt = self.opt
        dbh = opt.get('dbh', None)

        if dbh:
            yield from self.dbh_cursor(dbh, sql)
        else:
            with TpDbh(**opt) as dbh:
                yield from self.dbh_cursor(dbh, sql)

    def dbh_cursor(self, dbh, sql):
        opt = self.opt
        cursor = dbh.cursor()
        self.columns = [row[0] for row in cursor.description]
        try:
            cursor.execute(sql)
        except Exception as e:
            print(f'failed to execute sql: {e}')
            return None

        ReturnType = opt.get('ReturnType', 'DictList')

        if RetrunType == 'DictList':
            for row in cursor:
                yield dict(zip(columns, row))
        elif ReturnType == 'ListList':
            for row in cursor:
                yield row
        else:
            raise RuntimeError(f'unknown ReturnType={ReturnType}. opt={opt}')

        # parse() is not really needed if will run execute anyway. but is useful if we just want to check sql
        # syntax without running it.
        # https://www.oracle.com/technetwork/prez-python-queries-101587.html
        #
        # Not really required to be called because SQL statements are automatically parsed at the Execute stage.
        # It can be used to validate statements before executing them. When an error is detected in such a
        # statement, a DatabaseError exception is raised with a corresponding error message, most likely
        # "ORA-00900: invalid SQL statement, ORA-01031: insufficient privileges or ORA-00921: unexpected end of
        # SQL command."
        # cursor.parse(sq1)

    def __iter__(self):
        return self.iterator()


def run_sql(sql_list: List[str], **opt):
    with TpDbh(**opt) as td:
        for sql in sql_list:
            qr = QueryResults(dbh=td, ReturnType='DictList')
            columns = qr.columns
            print(columns)
            for row_dict in qr:
                print(row_dict)
    sql_dictlist = SqlDictList(sql, **opt)

    if sql_dictlist is None:
        return 1

    columns = sql_dictlist.columns

    need_close = False

    output = opt.get('SqlOutput', '-')

    if output == '-':
        ofh = sys.stdout
    else:
        ofh = open(output, 'w')
        need_close = True

    delimiter = opt.get('SqlDelimiter', ',')

    print(f'{delimiter.join(columns)}\n', file=ofh)

    for l in sql_dictlist.list_iterator():
        print(f'{delimiter.join(l)}\n', file=ofh)

    if need_close:
        ofh.close()

    return 0


def main():
    print(f'open a conn_file')
    pprint(unlock_conn('ADB_USER@AHOST', connfile='sqllib_conn_test.csv'))


if __name__ == '__main__':
    main()
