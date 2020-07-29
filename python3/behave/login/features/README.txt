https://pypi.org/project/behave-webdriver/

make sure chromedriver in PATH, otherwise, you get HOOK-ERROR
on linux
   tian@linux1:/home/tian/github/tpsup/python3/behave/examples$ which chromedriver
   /usr/bin/chromedriver

on windows
   C:\Users\william\github\tpsup\python3\behave\examples>where chromedriver
   C:\Users\william\chromedriver.exe

on Linux
   tian@linux1:/home/tian/github/tpsup/python3/behave/examples$ which behave
   /usr/local/bin/behave
   
   tian@linux1:/home/tian/github/tpsup/python3/behave/examples$ head /usr/local/bin/behave
   #!/usr/bin/python3
   ...
   
   tian@linux1:/home/tian/github/tpsup/python3/behave/examples/features$ behave .
   or
   tian@linux1:/home/tian/github/tpsup/python3/behave/examples$ behave features
   Feature: Sample Snippets test # features/myFeature.feature:1
     As a developer
     I should be able to use given text snippets
     Scenario: open URL                                                          # features/myFeature.feature:5
       Given the page url is not "http://webdriverjs.christian-bromann.com/"     # ../../../../../../../usr/local/lib/python3.6/dist-packages/behave_webdriver/steps/expectations.py:152 0.011s
       And I open the url "http://webdriverjs.christian-bromann.com/"            # ../../../../../../../usr/local/lib/python3.6/dist-packages/behave_webdriver/steps/actions_re.py:60 0.998s
       Then I expect that the url is "http://webdriverjs.christian-bromann.com/" # ../../../../../../../usr/local/lib/python3.6/dist-packages/behave_webdriver/steps/expectations.py:152 0.012s
       And I expect that the url is not "http://google.com"                      # ../../../../../../../usr/local/lib/python3.6/dist-packages/behave_webdriver/steps/expectations.py:152 0.006s
   
     Scenario: click on link                                          # features/myFeature.feature:12
       Given the title is not "two"                                   # ../../../../../../../usr/local/lib/python3.6/dist-packages/behave_webdriver/steps/expectations.py:25 0.005s
       And I open the url "http://webdriverjs.christian-bromann.com/" # ../../../../../../../usr/local/lib/python3.6/dist-packages/behave_webdriver/steps/actions_re.py:60 0.114s
       When I click on the link "two"                                 # ../../../../../../../usr/local/lib/python3.6/dist-packages/behave_webdriver/steps/actions.py:31 1.010s
       Then I expect that the title is "two"                          # ../../../../../../../usr/local/lib/python3.6/dist-packages/behave_webdriver/steps/expectations.py:25 0.005s
   
   1 feature passed, 0 failed, 0 skipped
   2 scenarios passed, 0 failed, 0 skipped
   8 steps passed, 0 failed, 0 skipped, 0 undefined
   Took 0m2.162s
   
on windows
   C:\Users\william\github\tpsup\python3\behave\examples>where behave
   C:\Program Files\Python37\Scripts\behave.exe
   
   C:\Users\william\github\tpsup\python3\behave\examples\features>behave .
   or
   C:\Users\william\github\tpsup\python3\behave\examples>behave features
   
   DevTools listening on ws://127.0.0.1:65001/devtools/browser/725806c8-6a3e-4fa2-8b7d-69cfbca57378
   Feature: Sample Snippets test # features/myFeature.feature:1
     As a developer
     I should be able to use given text snippets
     Scenario: open URL                                                          # features/myFeature.feature:5
       Given the page url is not "http://webdriverjs.christian-bromann.com/"     # ../../../../../../../program files/python37/lib/site-packages/behave_webdriver/steps/expectations.py:152
       And I open the url "http://webdriverjs.christian-bromann.com/"            # ../../../../../../../program files/python37/lib/site-packages/behave_webdriver/steps/actions_re.py:60
       Then I expect that the url is "http://webdriverjs.christian-bromann.com/" # ../../../../../../../program files/python37/lib/site-packages/behave_webdriver/steps/expectations.py:152
       And I expect that the url is not "http://google.com"                      # ../../../../../../../program files/python37/lib/site-packages/behave_webdriver/steps/expectations.py:152
   
     Scenario: click on link                                          # features/myFeature.feature:12
       Given the title is not "two"                                   # ../../../../../../../program files/python37/lib/site-packages/behave_webdriver/steps/expectations.py:25
       And I open the url "http://webdriverjs.christian-bromann.com/" # ../../../../../../../program files/python37/lib/site-packages/behave_webdriver/steps/actions_re.py:60
       When I click on the link "two"                                 # ../../../../../../../program files/python37/lib/site-packages/behave_webdriver/steps/actions.py:31
       Then I expect that the title is "two"                          # ../../../../../../../program files/python37/lib/site-packages/behave_webdriver/steps/expectations.py:25
   
   1 feature passed, 0 failed, 0 skipped
   2 scenarios passed, 0 failed, 0 skipped
   8 steps passed, 0 failed, 0 skipped, 0 undefined
   Took 0m6.095s
   
   
