# ptslnm -af url="file:///c:/Users/tian/sitebase/github/tpsup/python3/scripts/ptslnm_test_input.html"  steps_py="c:/Users/tian/sitebase/github/tpsup/python3/scripts/ptslnm_test_input_steps_py.py"   top

[
    # """
    #     click_xpath=//input[@id="user id"],
    #     click_css=#user id,
    #     xpath=//tr[class="non exist"]
    # """,
    'click_xpath=//input[@id="user id"],click_css=#user id,xpath=//tr[class="non exist"]',
    'ensureInput=helloWorld',
    "sleep=2",

    'click_xpath=//select[@id="Expertise"]',
    # "select=text,JavaScript",
    'ensureInput=JavaScript',
    "sleep=3",
    
    # test searching two elements
    # note: to fit into one string
    # 'xpath=//fieldset/legend[text()="Profile2"]/../input[@class="submit-btn"],xpath=//tr[@class="non exist"]',
    'xpath=//tr[@class="non exist"],xpath=//fieldset/legend[text()="Profile2"]/../input[@class="submit-btn"]',
    "click", 
    'gone_xpath=//select[@id="Expertise"]',
    "sleep=3",
]
