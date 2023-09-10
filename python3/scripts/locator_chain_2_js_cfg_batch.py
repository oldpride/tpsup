#!/usr/bin/env python
import datetime
import os
from typing import Union

import tpsup.envtools

import tpsup.csvtools
import tpsup.htmltools
import tpsup.seleniumtools_old
import tpsup.pstools
from pprint import pformat


our_cfg = {
    'extra_args': [
        # argparse's args
        {
            'dest': 'oprefix',
            'default': False,
            'action': 'store',
            'help': 'output with this prefix',
        },
        {
            'dest': 'trap',
            'default': False,
            'action': 'store_true',
            'help': 'add try{...}catch{...}',
        },
    ],

    'usage_example': '''
    - convert locator chain into javascript
    
    chrome-search://local-ntp/local-ntp.html
    
    # iframe001: id("backgroundImage")
    # shadow001: /html[@class="focus-outline-visible"]/body[1]/ntp-app[1]
    # shadow001.shadow002: /div[@id="content"]/ntp-iframe[@id="oneGoogleBar"]
    # shadow001.shadow002.iframe002: /iframe[@id="iframe"]
    # div.gb_Id     # <div class="gb_Id">Google apps</div>

    # in shadow, we can only use css selector to locate
    # but once in iframe, even if an iframe inside an shadow root, we can use xpath again.
    
    # from cmd.exe, 
    #   double quotes cannot be escaped, 
    #   single quote is just a letter, cannot do grkouping. 
    # therefore, xpath=//div[@class="gb_Id"] will not work on cmd.exe
    {{prog}} xpath=/html/body/ntp-app shadow css=ntp-iframe shadow "css=#iframe" iframe xpath=//div[3]
    
    # from bash
    {{prog}} xpath=/html/body/ntp-app shadow css=ntp-iframe shadow "css=#iframe" iframe 'xpath=//div[@class="gb_Id"]'
    
    # with output prefix
    {{prog}} xpath=/html/body/ntp-app shadow css=ntp-iframe shadow "css=#iframe" iframe xpath=//div[3] -oprefix "%TPSUP%/python3/scripts/locator_chain_test"
    
    ''',
}


def code(all_cfg, known, **opt):
    verbose = opt.get('verbose', 0)
    if verbose:
        print(f'from code(), known ={pformat(known)}')
        print(f'from code(), opt = {pformat(opt)}')

    dir = None
    prefix = None
    oprefix = opt.get('oprefix', None)
    if oprefix:
        dir = os.path.dirname(oprefix)
        prefix = os.path.basename(oprefix)

    locator_chain = known['REMAININGARGS']
    js_list = tpsup.seleniumtools_old.locator_chain_to_js_list(locator_chain)

    # print(f'js_list = {pformat(js_list)}')\
    i = 0
    for js in js_list:
        i += 1
        print("")
        print(f"-------------------- #{i} -----------------------")
        print(js)
        print("")
        if oprefix:
            os.makedirs(dir, exist_ok=True)
            file = f"{dir}/{prefix}{i}.js"
            print(f"writing to {file}")
            with open(file, 'w') as ofh:
                ofh.write(js)
                ofh.write('\n')
                ofh.close()


def parse_input_sub(input: Union[str, list], all_cfg: dict, **opt):
    return {'REMAININGARGS': input}
