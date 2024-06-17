@echo off

setlocal

:: the following two single quote look alike. but the first one is actually not a standard single quote.
::
rem
rem    If you don’t 
rem    If you don't 
rem 
:: i came to notice it when my pkill.cmd stopped working in the cygwin and gitbash at work.
::    even though that character is behind REM
::
:: the following was my test
::    cygwin  (mintty 3.5.0) at work: not working
::    gitbash (mintty 3.4.6) at work: not working
::    cmd.exe                at work:     working
::    cygwin  (mintty 3.4.0) at home:     working
::    gitbash (mintty 3.2.0) at home:     working
::    cmd.exe                at home:     working
::
:: the error i saw was
::    'etlocal' is not recognized as an internal or external command,
::    operable program or batch file

echo do you see any error?


endlocal




