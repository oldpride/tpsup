@echo off

if '%*'=='' (
   echo "usage: addpath new_part"
   exit /b
)

rem echo path=%path%

setlocal
set new=%1
set need=Y
rem how to split %path% which is delimited by ;
rem https://stackoverflow.com/questions/14879105/windows-path-variable-how-to-split-on-in-cmd-shell-again
for %%i in ("%path:;="; "%") do (
   rem %%i is double-quoted, eg, "C:\Users\william\AppData\Local\Android\Sdk\emulator" 
   rem therefore, when compare strings later, we need to use double quote on the other party too.
   rem echo checking %%i 

   rem /a/b can also show up as /a/b/
   rem bat doesn't support OR/AND logic
   rem https://stackoverflow.com/questions/2143187/logical-operators-and-or-in-dos-batch
   if %%i=="%new%" (
      echo path already has %%i
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

if '%need%'=='Y' (
   rem set path=a;b need double quotes. otherwise error: \Common was unexpected at this time.
   endlocal
   set "path=%path%;%new%"
   echo appended %new% to path
)
endlocal

