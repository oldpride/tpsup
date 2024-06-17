@echo off

:: ways to parse optional args
:: https://stackoverflow.com/questions/3973824/windows-bat-file-optional-argument-parsing
::
:: basename
set "prog=%~n0"
set action=append
set quiet=0
:check_optional
   :: shift doesn't work in a block, eg, in a if-block, therefore move it to outside
   :: https://stackoverflow.com/questions/17241184/windows-batch-shift-not-working-in-if-block
   set check_again=0

   :: single quotes vs double quotes
   ::    in window's batch, only double quotes groups. Single quotes just like any other chars except in For loop.
   ::    double quotes will pass through into the script. eg,
   ::       myprogram "A B C"
   ::    %1 will be "A B C" in script, with double quotes
   if '%1'=='-p'       ( 
      set action=prepend
      set check_again=1
   )
   if '%1'=='-prepend' (
      set action=prepend
      set check_again=1
   )
   if '%1'=='-q'       (
      set quiet=1
      set check_again=1
   )
   if '%1'=='-quiet'   (
      set quiet=1
      set check_again=1
   )
   if '%1'=='-d'       (
      @echo on
      set check_again=1
   )
   if '%1'=='-debug'   (
      @echo on
      set check_again=1
   )
   if '%check_again%' == '0' goto :finished_optional
shift & goto :check_optional

:finished_optional

if '%2' == '' (
   echo missing args
   goto :usage
)
   
if NOT '%3' == '' (
   echo more args than expected
   goto :usage
)
   
set var=%1
set new=%2

REM :windows batch has no escape char
REM :https://superuser.com/questions/279008/how-do-i-escape-spaces-in-command-line-in-windows-without-using-quotation-marks
REM :   see answer fro Pacerier

REM :bat variable of variable, ie, unix eval equivalent
REM :https://stackoverflow.com/questions/29696734/how-to-put-variable-value-inside-another-variable-name-in-batch

setlocal EnableDelayedExpansion

REM :remove all double quotes in arg
set new=%new:"=%

REM :Does string have a trailing slash? if so remove it
IF %new:~-1%==\ SET new=%new:~0,-1%

REM echo new=%new%

set value=!%var%!

set need=Y
if '%action%'=='append' (
   REM :how to split %path% which is delimited by ;
   REM :https://stackoverflow.com/questions/14879105/windows-path-variable-how-to-split-on-in-cmd-shell-again
   for %%i in ("%value:;="; "%") do (
      REM %%i  is double-quoted, eg, "C:\Users\william\AppData\Local\Android\Sdk\emulator" 
      REM %%~i is    not quoted, eg,  C:\Users\william\AppData\Local\Android\Sdk\emulator 
      REM therefore, when compare strings later, we need to use double quote on the other party too.
      REM echo checking %%~i 
      
      REM /a/b can also show up as /a/b/
      REM bat doesn't support OR/AND logic
      REM https://stackoverflow.com/questions/2143187/logical-operators-and-or-in-dos-batch
      set old=%%~i
   
      REM to debug, uncomment below
      REM echo old=!old!
   
      REM the following "if not" should be a "if-continue" pattern but batch script doesn't have "continue"
      if not "!old!"=="" (
         REM Does string have a trailing slash? if so remove it
         REM inside loop use ! instead of %
         IF !old:~-1!==\ SET old=!old:~0,-1!
      
         REM /I for case insensitive
         if /I "!old!"=="%new%" (
            if '%quiet%'== '0' echo %var% already has !old!
            set need=N
      
            rem break out from loop
            goto :endloop1
      
            rem or exit here
            rem bare 'exit' will poof the calling shell
            rem exit /b  
         ) else (
            rem echo not match
         ) 
      )
   )
)

:endloop1

if '%need%'=='N' (
   exit /b 0
)

REM :how pass variable from set local to global
REM :https://stackoverflow.com/questions/15494688/batch-script-make-setlocal-variable-accessed-by-other-batch-files
endlocal & (
   rem set path=a;b need double quotes. otherwise error: \Common was unexpected at this time.
   if '%action%'=='append' (
      set "%var%=%value%;%new%"
      if '%quiet%'== '0' echo appended "%new%" to %var%
   ) else (
      set "%var%=%new%;%value%"
      if '%quiet%'== '0' echo prepended "%new%" to %var%
   )
)
exit /b 0

rem : echo. is to print blank line (empty line)
:usage
   echo.
   echo usage:   
   echo.
   echo    %prog% [flags] var_name new_part
   echo.
   echo    -d, -debug     debug mode. besically turn on ECHO.
   echo    -p, -prepend   means prepend to PATH. default is to append to PATH 
   echo    -q, -quiet     quiet mode. don't print out actions. default is to not quiet 
   echo.
   echo example:
   echo.
   echo    %prog% PYTHONPATH %userprofile%\siteenv\github\tpsup\python3\lib
   echo.
   echo    %prog% PATH "C:\Program Files (x86)\Google\Chrome\Application"
   echo.
   echo caveat:  use double quotes for space/parenthesis in args as windows bat only use double
   echo          quotes to group. Single quotes cannot group.

   REM this is function return; it doesn't exit the script.
   REM no good way to exit script from inside a function
   exit /b 0
:eof
