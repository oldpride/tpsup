{
    'type': 'parallel',
    'action': {
        'paths' : [
            # 'parallel' allows you to handle individual path differently - define 'Success' and 'Failure' for each path.
            {
                'locator' : 'xpath=//iframe[1]',
                'Success': 'iframe',
            },
            {
                'locator' : 'css=p',
                'Success': 'code=print("this is unexpected. we should find iframe, not p")',
            },
        ],
        # 'action' level 'Success' and 'Failure' are optional.
        #'Success' : 'code=print("found")', # optional. If either one is found, Do this. default is None
        'Failure' : 'code=print("this is unexpected. we should find something")', 
    }
},
