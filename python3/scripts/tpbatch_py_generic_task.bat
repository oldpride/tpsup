@echo off

:: wrapper script 

:: this script set up env all way to venv.
:: it used in task scheduler which can only accept one script.

set "prog_task=%~n0"
set "dir=%~dp0"

call siteenv
:: if the above failed, run siteenv manually and try again. 

call p3env
call svenv

set "prog=%prog_task:_task=%"
call "%dir%\%prog%.bat" %*

call dvenv

