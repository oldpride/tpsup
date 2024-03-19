import re
import subprocess
import sys
from threading import Thread
import time
from queue import Queue, Empty

current_child = None

ON_POSIX = 'posix' in sys.builtin_module_names


def enqueue_output(out, queue):
    for line in iter(out.readline, b''):
        queue.put(line)
    out.close()


def init_child(cmd, method='subprocess', **opt):
    # non-blocking read
    # https://stackoverflow.com/questions/375427

    # https://stackoverflow.com/questions/31833897
    if method == 'subprocess':
        process = subprocess.Popen(cmd,
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE,
                                   stdin=subprocess.PIPE,
                                   #    bufsize=1,
                                   close_fds=ON_POSIX,
                                   # 1. without shell=True, 'cmd' is the path to executable.
                                   # built-in command like 'dir' will fail
                                   # with "The system cannot find the file specified".
                                   # so will doskey command fail. eg, 'ls' from "doskey ls=dir $*".
                                   # because they need to be sourced from profile first.
                                   # 2. with shell=True, 'cmd' will be a string.
                                   shell=True,
                                   **opt)

        queue = Queue()
        out_thread = Thread(target=enqueue_output, args=(process.stdout, queue))
        out_thread.daemon = True  # thread dies with the program
        out_thread.start()

        err_queue = Queue()
        err_thread = Thread(target=enqueue_output, args=(process.stderr, err_queue))
        err_thread.daemon = True
        err_thread.start()

    else:
        raise Exception(f"unsupported method={method}")

    child = {
        'method': method,
        'process': process,
        'out_queue': queue,
        'err_queue': err_queue
    }

    global current_child
    current_child = child

    return child


def clean_data(data):
    # remove control characters except tab
    # return re.sub(r'[^a-zA-Z0-9.~!@#$%^&*()=\[\]{}+|\\:;\'"?/<>, `_-]', '.', data)
    return data


def expect_child(patterns, child=None, logic='and', timeout=10, expect_interval=1, **opt):
    verbose = opt.get('verbose', 0)

    global current_child
    if not child:
        child = current_child

    # patterns is a list of dict, each dict has a
    # key 'pattern' and optional keys.
    # 'source' : 'stdout' or 'stderr', default is 'stdout'
    # patterns = [ {'pattern': 'password:'}, {'pattern': 'closed', 'source' : 'stderr'},]
    if not child:
        raise Exception("child is not initialized")

    if child['method'] == 'subprocess':
        match_results = patterns.copy()

        out_queue = child['out_queue']
        err_queue = child['err_queue']

        out_total = b''
        err_total = b''
        total_wait = 0

        while True:
            # https://github.com/xloem/nonblocking_stream_queue
            out_line = None
            err_line = None

            try:
                out_line = out_queue.get_nowait()
            except Empty:
                verbose and print("stdout, no data ready")
                pass

            try:
                err_line = err_queue.get_nowait()
            except Empty:
                verbose and print("stderr, no data ready")
                pass

            if not out_line and not err_line:
                if total_wait > timeout:
                    print(f"timeout after {timeout} seconds", file=sys.stderr)
                    break

                time.sleep(expect_interval)
                total_wait += expect_interval

                continue

            if out_line:
                out_total += out_line
                verbose > 1 and print(f"out: {clean_data(out_line)}")

            if err_line:
                err_total += err_line

                verbose > 1 and print(f"err: {clean_data(err_line)}")

            matched = None
            if logic == 'and':
                matched = True
                for i in range(len(match_results)):
                    pattern = match_results[i]

                    if pattern.get('matched', False):
                        continue

                    source = pattern.get('source', 'stdout')
                    if source == 'stdout':
                        data = out_total
                    else:
                        data = err_total

                    # TypeError: cannot use a string pattern on a bytes-like object
                    # if re.search(pattern['pattern'], data):
                    if re.search(pattern['pattern'].encode('utf-8'), data):
                        match_results[i]['matched'] = True
                        match_results[i]['data'] = data
                    else:
                        matched = False
                if matched:
                    break
            else:
                # logic == 'or'
                matched = False
                for i in range(len(match_results)):
                    pattern = match_results[i]

                    if pattern.get('matched', False):
                        continue

                    source = pattern.get('source', 'stdout')
                    if source == 'stdout':
                        data = out_total
                    else:
                        data = err_total

                    # TypeError: cannot use a string pattern on a bytes-like object
                    # if re.search(pattern['pattern'], data):
                    if re.search(pattern['pattern'].encode('utf-8'), data):
                        match_results[i]['matched'] = True
                        match_results[i]['data'] = data
                        matched = True
                        break

                if matched:
                    break

        ret = {
            'matched': matched,
            'out': out_total,
            'err': err_total,
            'match_results': match_results
        }

        return ret


def send_to_child(data: str = None, child=None, newline=True, **opt):
    global current_child
    if not child:
        child = current_child
    if not child:
        raise Exception("child is not initialized")

    if child['method'] == 'subprocess':
        if data:
            child['process'].stdin.write(data.encode('utf-8'))
        if newline:
            child['process'].stdin.write(b'\n')
        child['process'].stdin.flush()


def close_child(child=None, **opt):
    global current_child
    if not child:
        child = current_child

    if not child:
        raise Exception("child is not initialized")

    if child['method'] == 'subprocess':
        child['process'].stdin.close()
        return child['process'].wait()


def main():

    def test_codes():
        # password prompt is not using either stdout or stderr.
        # so it will not be captured by expect_child
        # init_child('sftp localhost')
        # expect_child([{'pattern': 'password:'}], timeout=2)

        # when shell=True, 'cmd' will be searched in PATH. therefore,
        # we can use both full path and command name.
        # init_child(r'c:\Users\william\sitebase\github\tpsup\cmd_exe\ps.cmd')
        init_child('ps')
        expect_child([{'pattern': 'Python'}], timeout=2)['matched'] == True

        # init_child('dir')   # 'dir' is a built-in command; it requires shell=True
        # expect_child([{'pattern': 'nettools.py'}], timeout=2)

        # init_child('dir no_such_file')
        # expect_child([{'pattern': 'File Not Found', 'source': 'stderr'}], timeout=2)

        # cmd.exe switches:
        # /C     Close: Run Command and then terminate and close.
        # /K     Keep:  Run Command and then keep the window open at the CMD prompt.
        #               This is useful for testing, e.g. to examine variables.
        init_child('cmd.exe /k')
        send_to_child()
        expect_child([{'pattern': '>'}], timeout=2)['matched'] == True
        send_to_child('dir')
        expect_child([{'pattern': 'nettools.py'}], timeout=2)['matched'] == True
        close_child() == 0

        # init_child('cmd.exe /k')
        init_child('gitbash')
        # no prompt during subprocess call
        # send_to_child()
        # expect_child([{'pattern': 'MINGW64'}], timeout=2)
        # send_to_child('sftp localhost')
        # expect_child([{'pattern': 'password:'}], timeout=5)
        send_to_child('uname -a')
        expect_child([{'pattern': 'MINGW64'}], timeout=2)['matched'] == True
        close_child() == 0
    from tpsup.testtools import test_lines
    test_lines(test_codes, source_globals=globals(), source_locals=locals())


if __name__ == '__main__':
    main()
