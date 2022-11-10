import sys
import functools


def silence_BrokenPipeError(func):
    @functools.wraps(func)
    def silenced(*args, **kwargs):
        result = None
        try:
            result = func(*args, **kwargs)
        except BrokenPipeError:
            sys.exit(1)
        return result
    return silenced


class TestOutput:
    def __init__(self, filename):
        if filename == '-':
            self.fh = sys.stdout
            self.fh.write = silence_BrokenPipeError(self.fh.write)
        else:
            self.fh = open(filename, 'rw')


def main():
    to = TestOutput('-')
    for i in range(0, 4000):
        to.fh.write(f'{i}\n')



if __name__ == '__main__':
    main()
