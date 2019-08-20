import unittest
import io
import os
import sys
import pprint
import time

import tpsup.sqllib


class TestSqllib(unittest.TestCase):
    def test_unlock_conn(self, verbose=0):
        _dir = os.path.dirname(sys.modules["tpsup.sqllib"].__file__)
        file = os.path.join(_dir, "sqllib_conn_test.csv")
        unlocked = tpsup.sqllib.unlock_conn('ADB_USER@AHOST', connfile=file)

        self.assertEqual(unlocked['string'], 'dbi:Oracle:host=AHOST.abc.com;service_name=AHOST.abc.com;port=1501')
        self.assertEqual(unlocked['unlocked_password'], 'Hello@123')


if __name__ == '__main__':
    unittest.main()
