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
from typing import List, Literal, Union

import tpsup.csvtools
import tpsup.env
from tpsup.lock import tpsup_unlock
import tpsup.printtools
from pprint import pformat
from tpsup.logtools import log_FileFuncLine, log_FileFuncLineObj


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

        # opt['MatchExps'] = [f'r["nickname"] == "{nickname}"']

        dictlist = list(tpsup.csvtools.QueryCsv(connfile, MatchExps=[
                        f'r["nickname"] == "{nickname}"'], **opt))

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
    # TpDbh vs dbh
    #    - dbh is a database handle, not from tpsup.
    #    - TpDbh is a wrapper class of dbh.
    def __init__(self,  **opt):
        self.dbh = opt.get('dbh', None)
        if self.dbh is None:
            nickname = opt.get('nickname', None)
            if nickname is None:
                raise RuntimeError(
                    f'nickname is required if dbh is not provided')

            # remove nickname from opt to avoid this error:
            # TypeError: Conn.__init__() got multiple values for argument 'nickname'
            del opt['nickname']  # remove key from dict
            conn = Conn(nickname, **opt)
            self.conn = conn
            self.close_dbh_on_exit = True
        else:
            self.close_dbh_on_exit = False

    def get_dbh(self):
        if self.dbh:
            return self.dbh

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
            # https://stackoverflow.com/questions/7744742
            # pyodc default not to auto commit.
            self.dbh = pyodbc.connect(conn_string,
                                      autocommit=True,
                                      )
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
        if self.dbh and self.close_dbh_on_exit:
            self.dbh.close()


class QueryResults:
    def __init__(self, sql, ReturnType: Literal['DictList', 'ListList'] = 'DictList', **opt):
        self.ReturnType = ReturnType
        self.need_close_dbh = False
        self.maxout = opt.get('maxout', -1)
        self.verbose = opt.get('verbose', 0)

        dbh = opt.get('dbh', None)

        if dbh is None:
            dbh = TpDbh(**opt).get_dbh()
            self.need_close_dbh = True

        self.cursor = dbh.cursor()
        self.dbh = dbh
        self.opt = opt
        self.no_column = False

        try:
            self.cursor.execute(sql)

            # dbh.commit()
            # this was needed by pyodbc, but was replaced by autocommit=true

        except Exception as e:
            sys.stderr.write(f'failed to execute sql: {e}\n')
            self.no_column = True
            return
            # return None

        if self.verbose:
            log_FileFuncLineObj('cursor.description=\n',
                                self.cursor.description)
            print()

        if self.cursor.description is None:
            self.no_column = True

            if self.cursor.rowcount != -1:
                # insert/update/delete will set rowcount; but
                # returns nothing else, ie, no column returned.
                print(f'affected rows = {self.cursor.rowcount}')
                # select/set/create/alter/drop will set rowcount to -1.
            else:
                if self.verbose:
                    log_FileFuncLine(
                        f"neither column returned nor rows affected: sql={sql}")
            return

        self.columns = [row[0] for row in self.cursor.description]

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def close(self):
        if self.need_close_dbh:
            self.dbh.close()

    def __iter__(self):
        if self.ReturnType == 'DictList':  # this is default
            # if the cursor returns List, use this
            gen = (dict(zip(self.columns, row)) for row in self.cursor)

            # if the cursor returns Dictionary, use this
            # gen = self.cursor

            if self.maxout >= 0:
                yield from itertools.islice(gen, self.maxout)
            else:
                yield from gen
        elif self.ReturnType == 'ListList':
            if self.maxout >= 0:
                yield from itertools.islice(self.cursor, self.maxout)
            else:
                yield from self.cursor
        else:
            raise RuntimeError(
                f'unknown ReturnType={self.ReturnType}. opt={self.opt}')

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


def parse_sql(sql: str, **opt):
    verbose = opt.get('verbose', 0)

    # this is to handle multi-commands sql
    # https://stackoverflow.com/questions/22709497/perl-dbi-mysql-how-to-run-multiple-queries-statements

    # first remove multi-line comments /* ... */
    sql = re.sub(r'/[*].*?[*]/', '', sql, flags=re.DOTALL)

    # then remove singlem-line comments -- ...
    sql = re.sub(r'--.*', '', sql)

    # to test: test_remove_sql_comment.pl

    if opt.get('NotSplitAtSemiColon', False):
        # then we split at GO
        sqls = re.split(r';\s*GO\s*;', sql, flags=re.IGNORECASE)
        sqls2 = []

        # add back GO statement as we use it to determine restart point
        for s in sqls:
            sqls2.append(s)
            sqls2.append('GO')

        sqls2.pop()  # remove the last 'GO' as it the default

        return sqls2
    else:
        # then split into single command
        sqls = sql.split(';')
        sqls = [s for s in sqls if s.strip() != '']

        if verbose > 1:
            log_FileFuncLine(f'sqls = \n{sqls}')

        return sqls


def run_sql(sql: Union[str, list], **opt):
    verbose = opt.get('verbose', 0)
    sqls = []
    is_single_sql = opt.get('is_single_sql', False)
    if isinstance(sql, str):
        if is_single_sql:
            sqls.append(sql)
        else:
            sqls.extend(parse_sql(sql, **opt))
    elif isinstance(sql, list):
        for s in sql:
            if is_single_sql:
                sqls.append(s)
            else:
                sqls.extend(parse_sql(s, **opt))
    else:
        raise RuntimeError(
            f'unsupported sql type: {type(sql)}, sql = {format(sql)}')

    # 'GO' vs ';'
    # https://stackoverflow.com/questions/1517527/what-is-the-difference-between-
    # and-go-in-t-sql
    # "
    #    GO is not actually a T-SQL command. The GO command was introduced by Microsoft
    #    tools as a way to separate batch statements such as the end of a stored
    #    procedure. GO is supported by the Microsoft SQL stack tools but is not
    #    formally part of other tools.
    #    "GO" is similar to ; in many cases, but does in fact signify the end of a batch.
    #    Each batch is committed when the "GO" statement is called, so if you have:
    #       SELECT * FROM table-that-does-not-exist;
    #       SELECT * FROM good-table;
    #    in your batch, then the good-table select will never get called because the
    #    first select will cause an error.
    #
    #    If you instead had:
    #       SELECT * FROM table-that-does-not-exist
    #       GO
    #       SELECT * FROM good-table
    #       GO
    #    The first select statement still causes an error, but since the second statement
    #    is in its own batch, it will still execute.
    #    GO has nothing to do with committing a transaction.
    # "
    ret = []

    with TpDbh(**opt) as dbh:
        # 'with' calls __enter__()
        # TpDBh.__enter__() returns a dbh

        opt2 = {}
        if 'dbh' not in opt:
            opt2['dbh'] = dbh

        for sql in sqls:
            if verbose:
                print(f'running single sql: {sql}', file=sys.stderr)
            qr = QueryResults(sql, **opt, **opt2)

            if qr.no_column:
                continue

            ret2 = []
            if qr.ReturnType == 'DictList':  # this is default
                ret2.extend(qr)
            else:  # qr.ReturnType == 'ListList':
                ret2.append(qr.columns)
                # ret2.extend(qr) # this is not working; it returns tuples
                ret2.extend([list(row) for row in qr])  # convert tuple to list

            if opt.get("RenderOutput", False):
                tpsup.printtools.render_arrays(ret2, **opt)
            elif outfile := opt.get("SqlOutput", None):
                if qr.ReturnType == 'DictList':
                    ret3 = ret2
                else:
                    # convert ListList to DictList
                    ret3 = []
                    for row in ret2:
                        ret3.append(dict(zip(qr.columns, row)))
                tpsup.csvtools.write_dictlist_to_csv(
                    ret3, qr.columns, outfile, **opt)

            ret.extend(ret2)

    return ret


def get_dbh(**opt):
    # reqiires dbh or nickname
    # to be compatible with perl SQL.pm
    return TpDbh(**opt).get_dbh()


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
    print(f'\ntest a mysql statement\n')
    run_sql(["SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED ;"],
            nickname='tptest@tpdbmysql')

    print()
    print('------------------------')
    print(f'\ntest ms sql database\n')
    run_sql(["SELECT * FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE='BASE TABLE'"],
            nickname="tptest@tpdbmssql")


if __name__ == '__main__':
    main()
