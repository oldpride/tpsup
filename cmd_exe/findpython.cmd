@echo off

REM batch script doesn't have a $# equivalent. the following script is the best so far
set argC=0
for %%x in (%*) do Set /A argC+=1
rem echo %argC%

REM batch script has no != operator. use NOT == instead
if NOT %argC% == 1 (
echo ERROR: wrong number of args
CALL :usage
exit /b 1
)

echo python path 
where python

REM newline
echo. 


python --version

echo. 

REM make sure to use \ as batch script don't take /, for example in del command
set tmpfile=%userprofile%\findpython_tmp.py
set module=%1

REM we cannot pipe to python directly as there seems to be hidden chars. instead, save the
REM the tmp script into a file, and then run the file
(
echo import sys
echo print^('search path: '^)
echo print^(^'\n   ^'.join^(sys.path^)^)
echo print^('\n'^)
echo.
echo import inspect
echo print^('trying to find %module% path'^)
echo import %module%
echo print^(inspect.getfile^(%module%^)^)
echo.
) > %tmpfile%
python %tmpfile%

del %tmpfile%

echo.
echo trying to find %module% package
REM: /i case-insentive
REM: /r regexp
REM: /c: literal string
python -m pip freeze |findstr /i /c:%module%
echo.

exit /b 0

rem http://steve-jansen.github.io/guides/windows-batch-scripting/part-7-functions.html
:usage
   echo usage:   findpython module_name
   echo example: findpython selenium

   REM this is function return; it doesn't exit the script. 
   REM no good way to exit script from inside a function
   exit /b 0


