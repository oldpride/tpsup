@echo off

set CMD_DIR=%~dp0

setlocal
   rem how to get parent dir
   rem https://stackoverflow.com/questions/34942604/get-parent-directory-of-a-specific-path-in-batch-script/54346165
   for %%I in ("%CMD_DIR%\..") do set "TPSUP=%%~fI"
endlocal & (
   set "CMD_DIR=%CMD_DIR%"
   set "TPSUP=%TPSUP%"
)

echo TPSUP=%TPSUP%

rem use 'call' to invoke external script; otherwise, the current script will exit after the external script
call %CMD_DIR%\addpath.cmd PATH %CMD_DIR%

rem blank line
echo. 
echo path=%path%

echo. 

rem https://superuser.com/questions/129969/navigate-to-previous-directory-in-windows-command-prompt
doskey cd=mycd $*
doskey ls=dir $*

p3env
