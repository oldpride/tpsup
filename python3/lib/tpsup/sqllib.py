# https://www.oracle.com/technetwork/prez-python-queries-101587.html

import cx_Oracle
from pprint import pprint, pformat
import os
import sys
from os.path import expanduser
import tpsup.csvwrapper
from tpsup.util import tpsup_unlock
import re


def unlock_conn(nickname: str, **opt):
    connfile = opt.get('connfile')
    if not connfile:
        # home-directory-in-python
        home = expanduser("~")
        connfile = home + "/.tpsup/conn.csv"

    ret = {'error': None}

    if not os.path.exists(connfile):
        ret['error'] = f'connection file {connfile} not found'
        return ret

    opt['MatchExps'] = [f'r["nickname"] == "{nickname}"']

    dictlist = []

    for d in tpsup.csvwrapper.CsvDictList(connfile, **opt):
        dictlist.append(d)

    if len(dictlist) == 0:
        ret['error'] = f"connection file {connfile} does not contain nickname = {nickname}"
        return ret
    elif len(dictlist) > 1:
        ret['error'] = f'connection file {connfile} has multiple nickname = {nickname} defined'
        return ret

    dbi_string = dictlist[0]['string']
    login = dictlist[0]['login']
    locked_password = dictlist[0]['password']

    # https://stackoverflow.com/questions/2554185/match-groups-in-python
    m0 = re.match("^dbi:(.+?):(.+)", dbi_string)
    if m0:
        ret["database"] = m0.group(1)
        pairs = m0.group(2)

        for pair in (pairs.split(";")):
            key, value = pair.split("=", 1)
            ret[key] = value

    ret["string"] = dbi_string
    ret["login"] = login
    ret["locked_password"] = locked_password
    ret["unlocked_password"] = tpsup.util.tpsup_unlock(locked_password)
    return ret


# cache
dbh_by_nickname = {}
current_dbh = None


def get_dbh(**opt):
    # https://stackoverflow.com/questions/1977362/how-to-create-module-wide-variables-in-python
    global dbh_by_nickname
    global current_dbh

    dbh = None

    if 'nickname' in opt:
        nickname = opt['nickname']
        del opt['nickname']

        if nickname in dbh_by_nickname:
            dbh = dbh_by_nickname[nickname]
            current_dbh = dbh
            return dbh

        info = unlock_conn(nickname, **opt)

        if info['error'] is not None:
            print(info['error'], file=sys.stderr)
            dbh = None
        else:
            if 'sid' in info:
                dsn_tns = cx_Oracle.makedsn(info['host'], info['port'], info['sid'])

                dbh = cx_Oracle.connect(info['login'], info['unlocked_password'], dsn_tns)
            elif 'service_name' in info:
                # use service name
                # https://stackoverflow.com/questions/51486739/how-to-connect-
                # to-an-oracle-database-using-cx-oracle-with-service-name-and-login
                # con = cx_Oracle.connect('username/password@host_name:port/
                # service_name')

                string = f'{info["login"]}/{info["unlocked_password"]}@{info["host"]}:{info["port"]}/{info["service_name"]}'
                dbh = cx_Oracle.connect(string)

        dbh_by_nickname[nickname] = dbh
        current_dbh = dbh
    elif current_dbh:
        dbh = current_dbh

    return dbh


class SqlDictList:
    # how to handle failure during class creation.
    # https://stackoverflow.com/questions/17332929/python-init-return-failure-to-create
    #
    # You could raise an exception when either assertion fail, or -, if you really don't want or can't
    # work with exceptions, you can write the  __new__ method in your classes -
    # in Python, __init__ is technically an "initializer" method - and it should fill in the attributes
    # and acquire some of the resources and others your object will need during its life cycle - However,
    # Python does define a real constructor, the __new__ method, which is called prior to __init__- and
    # unlike this, __new__ actually does return a value: the newly created (uninitialized) instance itself.

    # https://spyhce.com/blog/understanding-new-and-init
    #
    # Before diving into the actual implementations you need to know that __new__ accepts cls as it's first parameter
    # and __init__ accepts self, because when calling __new__ you actually don't have an instance yet, therefore no
    # self exists at that moment, whereas __init__ is called after __new__ and the instance is in place, so you can
    # use self with it.

    # how to set attr in __new__
    # https://stackoverflow.com/questions/54358665/python-set-attributes-during-object-creation-in-new
    def __new__(cls, sql: str, **opt):
        instance = super(SqlDictList, cls).__new__(cls)
        instance.sql = sql
        instance.opt = opt

        dbh = get_dbh(**opt)
        if not dbh:
            print(f'cannot open database connection', file=sys.stderr)
            return None

        # right now we re-use dbh, but we probably can re-use cursor instead. need more research here
        cursor = dbh.cursor()

        try:
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
            cursor.execute(sql)
        except Exception as e:
            print(f'failed to execute sql: {e}')
            return None
            # if we want to return None when instance creation fails, we must use __new__() because only __new__ can
            # return a value.
            # but if we used __init__(), it would not return anything, any the instance is always created. but we could
            # use an attribute to indicate any failure during __init__().
            # up to now, I don't see any benefit to pick either one in this case.

        instance.dbh = dbh
        instance.cursor = cursor
        instance.columns = [row[0] for row in cursor.description]

        return instance

    def iterator(self):
        columns = self.columns
        for row in self.cursor:
            yield dict(zip(columns, row))
        return

    def __iter__(self):
        return self.iterator()

    def __next__(self):
        return self.iterator()

    def list_iterator(self):
        columns = self.columns
        for row in self.cursor:
            yield row
        return


def run_sql(sql, **opt):
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