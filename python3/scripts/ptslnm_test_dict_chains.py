{
    # chain is a list of list of locators in parallel.
    #     locators are in parallel, but the chain in each locator is in sequence.
    'type': 'chains',          
    'action': {
        'paths' : [
            {
                'locator': [
                    "xpath=/html[1]/body[1]/iframe[1]",
                    "iframe",
                    "xpath=id('shadow_host')",
                    "shadow",
                    "css=#nested_shadow_host", 
                    "shadow",
                    "css=span2" # this doesn't exist. css=span exists.
                                # we on purpose make it fail, so that 
                                # below locator is executed.
                ],
                'Success': 'code=print("found unexpected")',    
            },
            {
                'locator': ["xpath=/html[1]/body[1]/iframe[1]",
                    "iframe",
                    "xpath=id('shadow_host')",
                    "shadow",
                    "css=iframe", 
                    "iframe",
                    "css=p" 
                ],
            },
        ],
        'Success': 'print=html',
        'Failure': 'code=print("not found")',
    },
},
