# ptslnm -af url="file:///c:/Users/tian/sitebase/github/tpsup/python3/scripts/ptslnm_test_input.html"  steps_py="c:/Users/tian/sitebase/github/tpsup/python3/scripts/ptslnm_test_input_steps_py.py"   top

[
    """
        click_xpath=//input[@id="user id"],
        click_css=#user id,
        xpath=//tr[class="non exist"]
    """,
        
    'string=myid',
    
    'print=element',

    # confirm text is myid
    'code=assert last_element.text == "myid"',

    'code=idtext=last_element.text',
    'if_not=last_element.text=="myid"',
    'return',
    'end_if',
       
    'sleep=1',
    
    "tab=4",
        
    # test getting element id
    """code=print(f'element id = {last_element.get_attribute("id")}, expecting DateOfBirth')""",
    """sleep=2""",
    'string=01232025', # mmddyyyy
    "comment=go to Date of Birth",
    'sleep=2',

    "shifttab=3",
    
    """code=print(f'element id = {last_element.get_attribute("id")}, expecting password')""",
    'string=mypassword',
    "sleep=2",


    'click_xpath=//select[@id="Expertise"]',
    "select=text,JavaScript",
    
    # NOTE: !!!
    # after selection, somehow I have to use xpath to get to the next element, tab
    # won't move to next element.
    # ['tab=2', 'select=value,2', 'select 2-Medium'],
    'click_xpath=//select[@id="Urgency"]',
    "select=value,2", 
    "comment=selected 2-Medium",
    "sleep=2",
    
    # test searching two elements
    # note: to fit into one string
    # 'xpath=//fieldset/legend[text()="Profile2"]/../input[@class="submit-btn"],xpath=//tr[@class="non exist"]',
    'xpath=//tr[@class="non exist"],xpath=//fieldset/legend[text()="Profile2"]/../input[@class="submit-btn"]',
    "click", 
    'gone_xpath=//select[@id="Expertise"]',
    "sleep=3",
]
