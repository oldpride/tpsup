@echo off

rem use 'call' to invoke external script; otherwise, the current script will exit after the external script
call %userprofile%/sitebase/github/tpsup/cmd_exe/addpath.cmd %userprofile%/sitebase/github/tpsup/cmd_exe

rem blank line
echo. 
echo path=%path%

echo. 

rem https://superuser.com/questions/129969/navigate-to-previous-directory-in-windows-command-prompt
doskey cd=mycd $*

p3env
