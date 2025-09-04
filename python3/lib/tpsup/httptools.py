from tpsup.nettools import is_tcp_open
import tpsup.envtools
import tpsup.cmdtools
import tpsup.pstools
import os
import time
import re

def handle_common_steps(step: str, **opt):
    '''
    handle steps common between appiumtools.py and seleniumtools.py
    '''
    debug = opt.get('debug', 0)
    dryrun = opt.get('dryrun', 0)

    ret = {'break_levels': 0, 'continue_levels': 0,}

    if step == 'start_http_server' or step == 'stop_http_server':
        return handle_common_steps(f'{step}=8000', **opt)
    elif m := re.match(r"(start|stop)_http_server=(\d+)", step, flags=re.IGNORECASE):
        action, port = m.groups()
        port = int(port)
        print(f"handle_common_steps: {action} http server on port {port}")
        if not dryrun:
            if action.lower() == 'start':
                start_http_server(port, **opt)
            elif action.lower() == 'stop':
                stop_http_server(port, **opt)
            else:
                return None
            
        ret['sucesss'] = True
        return ret
        

def start_http_server(port: int=8000, http_base: str=None, log:str = None, **opt):
    '''
    check if the port is occupied. if yes, return.
    start a simple http server under python3/scripts
    default log file is $homedir/http_server/port.log

    '''
    import http.server
    import socketserver

    debug = opt.get('debug', 0)
    dryrun = opt.get('dryrun', 0)

    if is_tcp_open('localhost', port):
        print(f"start_http_server: port {port} is occupied")
        return

    if not http_base:
        TPSUP = os.environ.get('TPSUP').replace("\\", "/")
        if not TPSUP:
            raise RuntimeError(f"TPSUP is not set")
        http_base = f"{TPSUP}/python3/scripts"
    # os.chdir(http_base)

    if not log:
        homedir = tpsup.envtools.get_home_dir().replace("\\", "/")
        log_dir = f"{homedir}/http_server"
        log = f"{log_dir}/{port}.log"
    else:
        log = log.replace("\\", "/")
        log_dir = os.path.dirname(log)

    print(f"log_dir={log_dir}")

    cmd = f"python -m http.server {port} -d {http_base} >{log} 2>&1 &"
    print(f"start_http_server: cmd={cmd} log={log}")
    if not dryrun:
        if not os.path.exists(log_dir):
            print(f"start_http_server: create log dir {log_dir}")
            os.makedirs(log_dir)
        tpsup.cmdtools.run_cmd(cmd, is_bash=True, **opt)

def stop_http_server(port: int=8000, **opt):
    '''
    check if the port is occupied. if not, return.
    kill the process
    '''

    debug = opt.get('debug', 0)
    dryrun = opt.get('dryrun', 0)

    if not is_tcp_open('localhost', port):
        print(f"stop_http_server: port {port} is not occupied")
        return

    proc_pattern = f"http.server {port}"
    tpsup.pstools.kill_procs([proc_pattern], **opt)

def main():
    start_http_server(port=8000, debug=1)
    time.sleep(2)
    stop_http_server(port=8000, debug=1)

if __name__ == "__main__":
    main()
        



    
