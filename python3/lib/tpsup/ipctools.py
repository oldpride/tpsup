import re
import subprocess
import time
import wexpect

current_child = None


def init_child(cmd, method='subprocess', **opt):
    if method == 'subprocess':
        child = subprocess.Popen(cmd,
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE,
                                 stdin=subprocess.PIPE,
                                 **opt)

    else:
        raise Exception(f"unsupported method={method}")

    child.method = method
    global current_child
    current_child = child

    return child


def clean_data(data):
    # remove control characters except tab
    # return re.sub(r'[^a-zA-Z0-9.~!@#$%^&*()=\[\]{}+|\\:;\'"?/<>, `_-]', '.', data)
    return data


def expect_child(patterns, child=None, logic='and', **opt):
    global current_child
    if not child:
        child = current_child

    # patterns is a list of dict, each dict has a
    # key 'pattern' and optional keys.
    # patterns = [ {'pattern': 'password:'}, {'pattern': 'closed'},]
    if not child:
        raise Exception("child is not initialized")

    if child.method == 'expect':
        # if logic == 'or':
        #     # convert patterns to list of strings for pexpect
        #     pexpect_patterns = [p['pattern'] for p in patterns]
        #     i = child.expect(pexpect_patterns, **opt)
        #     ret = [{'index': i, 'pattern': patterns[i], 'data': child.before}]
        #     return ret
        # elif logic == 'and':
        #     ret = []
        #     for p in patterns:
        #         i = child.expect([p['pattern']], **opt)
        #         ret.append({'index': i, 'pattern': p, 'data': child.before})
        #     return ret
        i = child.expect(['password:', pexpect.TIMEOUT, pexpect.EOF], **opt)
        if i == 1:
            print(f"timeout: {clean_data(child.before)}")
        elif i == 2:
            print(f"EOF: {clean_data(child.before)}")
    elif child.method == 'subprocess':
        # not supported yet
        raise Exception("subprocess method is not supported yet")


def send_to_child(data, child=None, **opt):
    global current_child
    if not child:
        child = current_child
    if not child:
        raise Exception("child is not initialized")

    if child.method == 'expect':
        child.sendline(data)
    elif child.method == 'subprocess':
        # not supported yet
        raise Exception("subprocess method is not supported yet")


def close_child(child=current_child, **opt):
    if not child:
        raise Exception("child is not initialized")

    if child.method == 'expect':
        child.close()
    elif child.method == 'subprocess':
        # not supported yet
        raise Exception("subprocess method is not supported yet")


def main():
    # init_child('sftp localhost', method='expect')
    # child = pexpect.popen_spawn.PopenSpawn("C:/Program Files/Git/bin/bash.exe")

    # time.sleep(2)
    # child.sendline("sftp localhost")
    # i = child.expect(['password', pexpect.TIMEOUT, pexpect.EOF], timeout=5)
    # if i == 0:
    #     print(f"try: {clean_data(child.before)}")
    # elif i == 1:
    #     print(f"timeout: {clean_data(child.before)}")
    # elif i == 2:
    #     print(f"EOF: {clean_data(child.before)}")

    # child = wexpect.spawn("sftp localhost")
    # child.expect('password:')
    # print(f"expected")
    # child.sendline('junk')
    # child.expect('password:')
    # child.close()

    child = wexpect.spawn('cmd.exe')
    print("here")
    child.expect('>')
    print(child.before)
    child.sendline('ls')
    child.expect('>')
    print(child.before)
    child.sendline('exit')

    exit(0)

    def test_codes():
        # test expect_child
        init_child('sftp localhost', method='expect')
        expect_child([{'pattern': 'password:'}])
        # send_to_child('junk\n')
        # expect_child([{'pattern': 'password:'}])
        # close_child()

    from tpsup.testtools import test_lines
    test_lines(test_codes, source_globals=globals(), source_locals=locals())


if __name__ == '__main__':
    main()
