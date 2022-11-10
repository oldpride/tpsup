Feature: Sample Snippets test
As a developer
I should be able to use given text snippets

Scenario: open URL
    Given the page url is not "https://livingstonchinese.org/LCA2"
    And   I open the url "https://livingstonchinese.org/"
    Then  I expect that the url is "https://livingstonchinese.org/LCA2/"
    And   I expect that the url is not "https://livingstonchinese.org/"


# https://help.crossbrowsertesting.com/selenium-testing/frameworks/behave/
Scenario: login
    Given the page url is "https://livingstonchinese.org/LCA2/"
    Then  I expect that the url is "https://livingstonchinese.org/LCA2/"
    When I enter my credentials
    When I click login
    Then I should see the login message


#Scenario: click on link
#Scenario: click on link
#    Given the title is not "two"
#    And   I open the url "http://webdriverjs.christian-bromann.com/"
#    When  I click on the link "two"
#    Then  I expect that the title is "two"
