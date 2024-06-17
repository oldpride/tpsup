@echo off

::dirname
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

REM change backslash to forward slash
REM set "HOME=%USERPROFILE:\=/%"
set "HOME=%USERPROFILE%%"

rem use 'call' to invoke external script; otherwise, the current script will exit after the external script
call "%CMD_DIR%\addpath.cmd" -q PATH "%CMD_DIR%"

REM now we should have addpath in PATH
call addpath -q PATH "%TPSUP%\vbs"
call addpath -q PATH "%SITESPEC%\bat"
call addpath -q PATH "%SITESPEC%\vbs"

:: blank line
:: echo. 
:: echo path=%path%
:: echo. 

if NOT DEFINED MYBASE set "MYBASE=%SITEBASE%
echo MYBASE=%MYBASE%

:: Four Points
:: 1. use double quotes in comment to hide special chars, eg, / 
::    https://stackoverflow.com/questions/63491984
::
:: 2. how to get basename
::    " https://stackoverflow.com/questions/3432851 "
::    "   %%~nI        - expands %%I to a file name only "
::    "   %%~xI        - expands %%I to a file extension only "
::    "for /F "delims=" %%I in ("c:\foo\bar baz.txt") do @echo %%~nxI "
::
:: 3. Comment is processed after Percent Expansion
::    https://stackoverflow.com/questions/73587662
::
:: 4. use double Percent in script, use single Percent on command line
::    same link above
::
for /F "delims=" %%I in ("%SITESPEC%") do set "SPECNAME=%%~nxI" 
echo SPECNAME=%SPECNAME%

rem https://superuser.com/questions/129969/navigate-to-previous-directory-in-windows-command-prompt
doskey cd=mycd $*
doskey ls=dir $*

rem to remove doskey (aka macro)
rem doskey cd=


rem p3env
rem
