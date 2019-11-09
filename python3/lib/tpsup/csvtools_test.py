# https://docs.python.org/3/library/unittest.html
#
# You can place the definitions of test cases and test suites in the same modules as the code they are to test (such
# as widget.py), but there are several advantages to placing the test code in a separate module,
# such as test_widget.py:
# The test module can be run standalone from the command line.
# The test code can more easily be separated from shipped code.
# There is less temptation to change test code to fit the code it tests without a good reason.
# Test code should be modified much less frequently than the code it tests.
# Tested code can be refactored more easily.
# Tests for modules written in C must be in separate modules anyway, so why not be consistent?
# If the testing strategy changes, there is no need to change the source code.
#
# tian@linux1:/home/tian/github/tpsup/python3/lib/tpsup$ python3 -m unittest *_test.py
# ----------------------------------------------------------------------
# Ran 0 tests in 0.000s
# OK

import unittest
import io
import os
import sys
import pprint
import time

import tpsup.csvtools


class TestCsvTools(unittest.TestCase):
    def test_patterns(self, verbose=0):
        # https://docs.python.org/3/library/pkgutil.html
        # pprint.pprint(sys.modules)
        _dir = os.path.dirname(sys.modules["tpsup.csvtools"].__file__)
        file = os.path.join(_dir, "csvtools_test.csv")
        s = io.StringIO()
        with tpsup.csvtools.QueryCsv(file, MatchPatterns=[',S'], ExcludePatterns=['Smith'], verbose=verbose) as qc:
            for row in qc:
                print(f'{row}', file=s, end='')

        expected_string = "{'alpha': 'd', 'number': '3', 'name': 'Stephen'}"

        self.assertEqual(s.getvalue(), expected_string)

    def test_expressions(self, verbose=0):
        # https://docs.python.org/3/library/pkgutil.html
        # pprint.pprint(sys.modules)
        _dir = os.path.dirname(sys.modules["tpsup.csvtools"].__file__)
        file = os.path.join(_dir, "csvtools_test.csv")
        s = io.StringIO()
        # fh = open('/etc/passwd', 'r')
        # print(s)
        # print(fh)
        # print(isinstance(s, io.IOBase))
        # print(isinstance(fh, io.IOBase))
        tpsup.csvtools.QueryCsv(filename=file,
                                MatchExps=['str(r["name"]).startswith("J")'],
                                ExcludeExps=['int(r["number"])>2'],
                                TempExps={'tempcol1': 'r["name"]+"-"+r["number"]'},
                                ExportExps={'exportcol1': 'r["tempcol1"] + "-confirmed"'},
                                verbose=verbose).output(filename=s)

        # https://stackoverflow.com/questions/3191528/csv-in-python-adding-an-extra-carriage-return-on-windows
        # \n vs \r\n
        expected_string = "alpha,number,name,exportcol1\r\nb,1,John,John-1-confirmed\r\n"

        self.assertEqual(s.getvalue(), expected_string)


if __name__ == '__main__':
    unittest.main()
