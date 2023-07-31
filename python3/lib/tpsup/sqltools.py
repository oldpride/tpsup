# oracle
try:
    import cx_Oracle
except ImportError:
    pass

# ms sql odbc
try:
    import pyodbc
except ImportError:
    pass

# mysql
try:
    import pymysql.cursors
    # pip install pymysql
except ImportError:
    pass

import itertools
import os
import re
import sys
from typing import List

import tpsup.csvtools
import tpsup.csvtools
import tpsup.env
from tpsup.lock import tpsup_unlock


class Conn:
    def __init__(self, nickname: str, **opt):
        env = tpsup.env.Env()
        connfile = opt.get('connfile', None)
        if connfile is None:
            # connfile = expanduser("~") + "/.tpsup/conn.csv"
            home_dir = env.home_dir
            connfile = home_dir + "/.tpsup/conn.csv"

        if not os.path.exists(connfile):
            raise RuntimeError(f'connection file {connfile} not found')

        if env.isLinux:
            st = os.stat(connfile)
            file_perm = st.st_mode & 0o777

            if file_perm != 0o600:
                raise RuntimeError(
                    f'{connfile} permission is {file_perm:o}; required 600')

        self.connfile = connfile
        self.env = env

        opt['MatchExps'] = [f'r["nickname"] == "{nickname}"']

        dictlist = list(tpsup.csvtools.QueryCsv(connfile, **opt))

        if len(dictlist) == 0:
            raise RuntimeError(
                f"connection file {connfile} does not contain nickname = {nickname}: {dictlist}")
        elif len(dictlist) > 1:
            raise RuntimeError(
                f'connection file {connfile} has multiple nickname = {nickname} defined: {dictlist}')

        self.dbi_string = dictlist[0]['string']
        self.login = dictlist[0]['login']
        self.locked_password = dictlist[0]['password']

        # https://stackoverflow.com/questions/2554185/match-groups-in-python
        m0 = re.match("^dbi:(.+?):(.+)", self.dbi_string)
        if m0:
            self.__dict__['dbtype'] = m0.group(1)
            pairs = m0.group(2)

            for pair in (pairs.split(";")):
                key, value = pair.split("=", 1)
                self.__dict__[key.lower()] = value

        self.string = self.dbi_string
        self.unlocked_password = tpsup_unlock(self.locked_password)

    def __str__(self):
        strings = []
        for attr in self.__dict__:
            if attr == 'unlocked_password':
                strings.append(f'{attr} = ...')
            else:
                strings.append(f'{attr} = {self.__dict__[attr]}')
        return '\n'.join(strings)


class TpDbh:
    def __init__(self, nickname: str, **opt):
        conn = Conn(nickname, **opt)
        self.conn = conn
        self.dbh = None

    def get_dbh(self):
        conn = self.conn

        if re.match("^dbi:Oracle:.+", conn.dbi_string, re.IGNORECASE):
            if hasattr(conn, 'sid'):
                dsn_tns = cx_Oracle.makedsn(conn.host, conn.port, conn.sid)
                self.dbh = cx_Oracle.connect(
                    conn.login, conn.unlocked_password, dsn_tns)
            elif hasattr(conn, 'service_name'):
                # use service name
                # https://stackoverflow.com/questions/51486739/how-to-connect-
                # to-an-oracle-database-using-cx-oracle-with-service-name-and-login
                # con = cx_Oracle.connect('username/password@host_name:port/
                # service_name')

                string = f'{conn.login}/{conn.unlocked_password}@{conn.host}:{conn.port}/{conn.service_name}'
                self.dbh = cx_Oracle.connect(string)
            else:
                raise RuntimeError(
                    f"unsupported oracle dbi_string {conn.dbi_string}")
        elif re.match("^dbi:ODBC:.+", conn.dbi_string, re.IGNORECASE):
            conn_string = f'DRIVER={conn.driver};SERVER={conn.server};DATABASE={conn.database};UID={conn.login};' \
                          f'PWD={conn.unlocked_password}'
            self.dbh = pyodbc.connect(conn_string)
        elif re.match("^dbi:mysql:.+", conn.dbi_string, re.IGNORECASE):
            # https://github.com/PyMySQL/PyMySQL
            self.dbh = pymysql.connect(host=conn.host,
                                       user=conn.login,
                                       password=conn.unlocked_password,
                                       db=conn.database,
                                       charset='utf8mb4',
                                       # cursorclass=pymysql.cursors.DictCursor # don't use this as it will return dict.
                                       )
        else:
            raise RuntimeError(
                f"unknown database dbi_string {conn.dbi_string}")

        return self.dbh

    def __enter__(self):
        return self.get_dbh()

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.dbh:
            self.dbh.close()


class QueryResults:
    def __init__(self, sql, **opt):
        self.return_type = opt.get('ReturnType', 'DictList')
        self.need_close_dbh = False
        self.maxout = opt.get('maxout', -1)

        dbh = opt.get('dbh', None)

        if dbh is None:
            dbh = TpDbh(**opt)
            self.need_close_dbh = True

        self.cursor = dbh.cursor()
        self.dbh = dbh
        self.opt = opt

        try:
            self.cursor.execute(sql)
        except Exception as e:
            sys.stderr.write(f'failed to execute sql: {e}\n')
            # return None

        self.columns = [row[0] for row in self.cursor.description]

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def close(self):
        if self.need_close_dbh:
            self.dbh.close()

    def __iter__(self):
        if self.return_type == 'DictList':
            # if the cursor returns List, use this
            gen = (dict(zip(self.columns, row)) for row in self.cursor)

            # if the cursor returns Dictionary, use this
            # gen = self.cursor

            if self.maxout >= 0:
                yield from itertools.islice(gen, self.maxout)
            else:
                yield from gen
        elif self.return_type == 'ListList':
            if self.maxout >= 0:
                yield from itertools.islice(self.cursor, self.maxout)
            else:
                yield from self.cursor
        else:
            raise RuntimeError(
                f'unknown ReturnType={self.return_type}. opt={self.opt}')

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


def unlock_conn(nickname: str, **opt):
    try:
        conn = Conn(nickname, **opt)
    except Exception as e:
        sys.stderr.write(f'{e}\n')
        return None
    else:
        return conn


def run_sql(sql_list: List[str], **opt):
    with TpDbh(**opt) as td:
        for sql in sql_list:
            qr = QueryResults(sql, dbh=td, **opt)
            # for row in qr:
            #     print(row)
            tpsup.csvtools.write_dictlist_to_csv(
                qr, qr.columns, opt.get('filename', sys.stdout), **opt)


def get_dbh(nickname: str, **opt):
    # to be compatible with perl SQL.pm
    return TpDbh(nickname, **opt).get_dbh()


def test_mysql():
    dbh = TpDbh(nickname='tian@tiandb').get_dbh()
    with dbh.cursor() as cursor:
        sql = "SELECT * FROM tblMembers"
        cursor.execute(sql)
        for row in cursor:
            print(row)

    # this works too
    # with TpDbh(nickname='tian@tiandb') as td:
    #     cursor = td.cursor()
    #     sql = "SELECT * FROM tblMembers"
    #     cursor.execute(sql)
    #     for row in cursor:
    #         print(row)


def main():
    print()
    print('------------------------')
    print(f'\nparse conn_file for oracle\n')
    print(unlock_conn('ora_user@ora_db', connfile='sqltools_conn_example.csv'))

    print()
    print('------------------------')
    print(f'\nparse conn_file for ms sql\n')
    print(unlock_conn('sql_user@sql_db', connfile='sqltools_conn_example.csv'))

    print()
    print('------------------------')
    print(f'\ntest a mysql database\n')
    run_sql(["select * from tblMembers"], nickname='tian@tiandb')

    print()
    print('------------------------')
    print(f'\none more test mysql\n')
    test_mysql()

    print()
    print('------------------------')
    print(f'\ntest ms sql database\n')
    run_sql(["SELECT * FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE='BASE TABLE'"],
            nickname="tptest@tpdbmssql")


if __name__ == '__main__':
    main()
