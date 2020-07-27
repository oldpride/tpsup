import unittest
import io
import os
import sys
import pprint
import time

import tpsup.lock


class TestLock(unittest.TestCase):
    def test_tpsup_lock(self, verbose=0):
        actual_string = tpsup.lock.tpsup_lock('Hello@123')

        expected_string = "%09%06%0F%05%00%03%5E%5CU"

        self.assertEqual(actual_string, expected_string)

    def test_tpsup_unlock(self, verbose=0):
        actual_string = tpsup.lock.tpsup_unlock('%09%06%0F%05%00%03%5E%5CU')

        expected_string = "Hello@123"

        self.assertEqual(actual_string, expected_string)


if __name__ == '__main__':
    unittest.main()
