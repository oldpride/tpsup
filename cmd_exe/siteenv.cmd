@echo off

rem: copy this file to %USERPROFILE%, that is, C:/Users/%USERNAME%

rem: 1. don't use setx
rem:    setx vs set
rem:       setx var value     permanently change
rem:       set  var=value     only change the current shell
rem: 2. don't use quotes, for example, below. this would make one big part 
rem:       set PATH="%PATH:%userprofile%/site..."
set PATH=%PATH%;%userprofile%/sitebase/github/tpsup/cmd_exe

tpsup
