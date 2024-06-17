@echo off

REM :batch script doesn't have a $# EQUivalent. the following script is the best so far
REM /A means the variable is numberic
set argC=0
for %%x in (%*) do Set /A argC+=1
REM :echo %argC%

if %argC% == 0 (
   echo ERROR: missing args
   call :usage
   exit /b 1
)

set action=append
if "%1"=="-p" (
   REM shift doesn't work in a block
   REM https://stackoverflow.com/questions/17241184/windows-batch-shift-not-working-in-if-block
   REM   shift
   REM   echo %1
   REM therefore, we have to use the following awkwardness
 
   set action=prepend
   set var=%2
   set new=%3
   set /A expectNum=3
) else (
   set var=%1
   set new=%2
   set /A expectNum=2
)

REM :batch script has no != operator. use NOT == instead
if NOT %argC% == %expectNum% (
   echo ERROR:   addpath wrong number of args. got %argC%, expected %expectNum%. args=%*
   call :usage
   exit /b 1
)

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

if '%action%'=='append' (
   set need=Y
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
            echo %var% already has !old!
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
) else (
   set "%var%=%new%;%value%"
   echo prepended "%new%" to %var%
   exit /b 0
)

:endloop1

if '%need%'=='N' (
   exit /b 0
)

REM :how pass variable from set local to global
REM :https://stackoverflow.com/questions/15494688/batch-script-make-setlocal-variable-accessed-by-other-batch-files
endlocal & (
   rem set path=a;b need double quotes. otherwise error: \Common was unexpected at this time.
   set "%var%=%value%;%new%"
   echo appended "%new%" to %var%
)
exit /b 0

rem : echo. is to print blank line (empty line)
:usage
   echo.
   echo usage:   
   echo.
   echo    addpath [-p] var_name new_part
   echo.
   echo    -p  means prepend to PATH. default is to append to PATH 
   echo.
   echo example:
   echo.
   echo    addpath PYTHONPATH %userprofile%\siteenv\github\tpsup\python3\lib
   echo.
   echo    addpath PATH "C:\Program Files (x86)\Google\Chrome\Application"
   echo.
   echo caveat:  use double quotes for space/parenthesis in args as windows bat has no escape

   REM this is function return; it doesn't exit the script.
   REM no good way to exit script from inside a function
   exit /b 0

