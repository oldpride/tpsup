@echo off

setlocal EnableDelayedExpansion
REM batch script doesn't have a $# equivalent. the following script is the best so far
set argC=0
for %%x in (%*) do Set /A argC+=1
@rem echo %argC%

@REM batch script has no != operator. use NOT == instead
if %argC% == 0 (
   @echo ERROR: wrong number of args. got %argC%, expected 2. args=%*
   @echo userage: 
   @echo    rm     path1 path2 ...
   @echo    rm     path1 path2 ...
   @echo or use windows commands:
   @echo    del   /q /s file1 file2 ...
   @echo    rmdir /q /s dir1 dir2 ...
   @echo          /q quiet,  /s recurisve
   @echo    powershell -ExecutionPolicy Bypass remove-item -fo -r -path path1, path2, ...
   exit /b
)

@rem OR operator in windows batch can be implemented using this pattern
@rem    https://stackoverflow.com/questions/8438511/if-or-if-in-a-windows-batch-file
set "unix_style="
if "%1" == "-fr" set unix_style=1
if "%1" == "-rf" set unix_style=1
if defined unix_style (
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
         set "files=!files!, %%a" 
      ) else ( 
         set "files=%%a" 
      )
   )
)

@rem echo %files%

if defined unix_style (
   @rem without setting EnableDelayedExpansion, 'echo %varible%' inside if statement won't work for
   @rem variables created inside the if statement.
   @rem    https://stackoverflow.com/questions/9102422/windows-batch-set-inside-if-not-working
   @rem       "var2 is set, but the expansion in the line echo %var2% occurs before the block is executed."
   call powershell -ExecutionPolicy Bypass remove-item -fo -r -ErrorAction SilentlyContinue -path %files% 
) else (
   call powershell -ExecutionPolicy Bypass remove-item -path %files%
)
endlocal
