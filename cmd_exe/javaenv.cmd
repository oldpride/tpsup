@echo off

setlocal EnableDelayedExpansion
set "prog=%~n0"

REM batch script doesn't have a $# equivalent. the following script is the best so far
set argC=0
for %%x in (%*) do Set /A argC+=1
rem echo %argC%

if NOT %argC% == 1 (
   echo ERROR:   wrong number of args. got %argC%, expected 1. args=%*
   echo usage:   %prog%  check
   echo          %prog%  version
   echo.
   echo          set java/jdk JAVA_HOME
   echo.
   echo example: %prog%  check
   echo          %prog%  1.8
   exit /b
)

set var=%1

set "JAVABASE=C:\Program Files\Java"

if %var% == check (
   echo checking java version
   dir /b /ad "%JAVABASE%\*"
   exit /b
)

set "found=N"
for /d %%a in (jdk, jre) do (
   rem dir /b /ad "%JAVABASE%\%%a%var%*" "%JAVABASE%\%%a-%var%*"
   rem echo done

   for /f %%i in ('dir /b /ad "%JAVABASE%\%%a%var%*" "%JAVABASE%\%%a-%var%*"') do (
    set "output=%%i"
   )

   rem setting var within loop must use
   rem     setlocal EnableDelayedExpansion
   rem otherwise the value would not be used inside loop or passed
   rem to outside the loop.
   rem https://stackoverflow.com/questions/13805187/
   rem echo output=!output!

   if "!output!"=="" (
      echo %%a %var% not found
    ) else (
      echo found "!output!"
      set "found=Y"
      rem break out loop
      goto :break
    )
)
:break

endlocal & (
   if "%found%"=="N" (
      echo java version %var% not found: neither jdk nor jre
      exit /b
   ) else (
      set "JAVA_HOME=%JAVABASE%\%output%"
      call addpath.cmd -p PATH "%JAVABASE%\%output%\bin"
   )
)
echo.
echo JAVA_HOME=%JAVA_HOME%
echo. 
echo executables:
call which java
echo.
call which javac
echo.
call which jar

