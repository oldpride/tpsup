import unittest
import io
import os
import sys
import pprint
import time

import tpsup.sqltools


class TestSqltools(unittest.TestCase):
    def test_unlock_conn_oracle(self, verbose=0):
        _dir = os.path.dirname(sys.modules["tpsup.sqltools"].__file__)
        file = os.path.join(_dir, "sqltools_conn_example.csv")
        conn = tpsup.sqltools.unlock_conn('ora_user@ora_db', connfile=file)

        self.assertEqual(conn.string, 'dbi:Oracle:host=AHOST.abc.com;service_name=AHOST.abc.com;port=1501')
        self.assertEqual(conn.unlocked_password, 'Hello@123')

    def test_unlock_conn_mssql(self, verbose=0):
        _dir = os.path.dirname(sys.modules["tpsup.sqltools"].__file__)
        file = os.path.join(_dir, "sqltools_conn_example.csv")
        conn = tpsup.sqltools.unlock_conn('sql_user@sql_db', connfile=file)

        self.assertEqual(conn.string,
                         'dbi:ODBC:DRIVER={ODBC Driver 11 for SQL Server};SERVER=AHOST.abc.com,1502;database=app1')
        self.assertEqual(conn.unlocked_password, 'Hello@123')


if __name__ == '__main__':
    unittest.main()
