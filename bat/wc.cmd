@echo off

setlocal EnableDelayedExpansion
REM batch script doesn't have a $# equivalent. the following script is the best so far
set argC=0
for %%x in (%*) do Set /A argC+=1
@rem echo %argC%

@REM ^ is the escape char
@REM batch script has no != operator. use NOT == instead
if %argC% == 0 (
   @echo ERROR: wrong number of args. got %argC%, expected ^>=1. args=%*
   @echo userage: 
   @echo    wc -l README.txt
   @echo    type README.txt ^| wc -l
   exit /b
)

if "%1" == "-l" (
   set start=1
) else (
   set start=0
)

@rem declare a variable, but not defined
set "files="

@rem shift away the -fr
@rem separate args by ", "
set /a idx=0
for %%a in (%*) do (
   @rem echo %%a
   set /a "idx+=1"
   if !idx! gtr %start% ( 
      if defined files ( 
         set "files=!files! %%a" 
      ) else ( 
         set "files=%%a" 
      )
   )
)

@rem echo %files%

find /c /v "" %files% 

endlocal
