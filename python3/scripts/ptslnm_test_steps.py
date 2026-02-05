# ptslnm -af url="file:///c:/Users/tian/sitebase/github/tpsup/python3/scripts/iframe_over_shadow_test_main.html"  steps_py="c:/Users/tian/sitebase/github/tpsup/python3/scripts/ptslnm_test_steps_py.py"   top

[
    'sleep=1', 
    'xpath=/html[1]/body[1]/iframe[1]', 'iframe', 
    'debug=after=url,consolelog', 
    "xpath=id('shadow_host')", 'shadow', 
    'css=#nested_shadow_host', 'shadow', 
    'css=span'
]
