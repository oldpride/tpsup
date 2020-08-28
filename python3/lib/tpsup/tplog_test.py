import unittest
import unittest.mock
import io
from tpsup.tplog import get_logger


class test_tplog(unittest.TestCase):
    def test_logging_levels(self, verbose=0):
        with unittest.mock.patch('sys.stderr', new=io.StringIO()) as fake_stderr:  # fake stderr, cookbook p566
            logger = get_logger()  # must start the logger after the patching
            logger.info("This is a info log")  # logger writes to stderr
            # 20200825:21:56:59,434 INFO     [tplog_test.py:test_logging_levels:13] This is a info log
            stderr = fake_stderr.getvalue()
            self.assertRegex(stderr, 'This is a info log')

if __name__ == '__main__':
    unittest.main()
