@echo off

REM batch script doesn't have a $# equivalent. the following script is the best so far
set argC=0
for %%x in (%*) do Set /A argC+=1
rem echo %argC%

REM batch script has no != operator. use NOT == instead
if NOT %argC% == 2 (
   echo ERROR:   addpath wrong number of args. got %argC%, expected 2. args=%*
   echo usage:   addpath var_name new_part
   echo example: addpath PYTHONPATH %userprofile%\siteenv\github\tpsup\python3\lib
   echo          addpath PATH "C:\Program Files (x86)\Google\Chrome\Application"
   echo caveat:  use double quotes for space/parenthesis in args as windows bat has no escape
   exit /b
)

rem windows batch has no escape char
rem https://superuser.com/questions/279008/how-do-i-escape-spaces-in-command-line-in-windows-without-using-quotation-marks
rem    see answer fro Pacerier

rem bat variable of variable, ie, unix eval equivalent
rem https://stackoverflow.com/questions/29696734/how-to-put-variable-value-inside-another-variable-name-in-batch

setlocal EnableDelayedExpansion

set var=%1
set new=%2

rem remove all double quotes in arg
set new=%new:"=%

echo new=%new%

set value=!%var%!

set need=Y
rem how to split %path% which is delimited by ;
rem https://stackoverflow.com/questions/14879105/windows-path-variable-how-to-split-on-in-cmd-shell-again
for %%i in ("%value:;="; "%") do (
   rem %%i  is double-quoted, eg, "C:\Users\william\AppData\Local\Android\Sdk\emulator" 
   rem %%~i is    not quoted, eg,  C:\Users\william\AppData\Local\Android\Sdk\emulator 
   rem therefore, when compare strings later, we need to use double quote on the other party too.
   rem echo checking %%~i 

   rem /a/b can also show up as /a/b/
   rem bat doesn't support OR/AND logic
   rem https://stackoverflow.com/questions/2143187/logical-operators-and-or-in-dos-batch
   if "%%~i"=="%new%" (
      echo %var% already has %%i
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
:endloop1

if '%need%'=='N' (
   exit /b
)

rem how pass variable from set local to global
rem https://stackoverflow.com/questions/15494688/batch-script-make-setlocal-variable-accessed-by-other-batch-files
endlocal & (
   rem set path=a;b need double quotes. otherwise error: \Common was unexpected at this time.
   set "%var%=%value%;%new%"
   echo appended "%new%" to %var%
)
