@echo off

:: setlocal can be nested
setlocal EnableDelayedExpansion
:: when EnableDelayedExpansion is set, %var% becomes !var!, except in IF's condition part.
::    

:: ways to parse optional args
:: https://stackoverflow.com/questions/3973824/windows-bat-file-optional-argument-parsing
::
set "prog=%~n0"
:check_optional
   :: shift doesn't work in a block, eg, in a if-block, therefore move it to outside
   :: https://stackoverflow.com/questions/17241184/windows-batch-shift-not-working-in-if-block
   set check_again=0
   if '%1'=='-d'       (
      @echo on
      set check_again=1
      goto :shift_once
   )
   if %check_again% == 0 goto :finished_optional
:shift_twice
shift
:shift_once
shift 
goto :check_optional

:finished_optional

:kcd
if '%2' == '' (
   echo missing args
   goto :usage
)
   
if NOT '%3' == '' (
   echo more args than expected
   goto :usage
)


set old=%1
set new=%2

REM before endlocal, use !var_name! to get the new value, except IF's condition part.
REM after endlocal, use %var_name%

set old_dir=%cd%

REM string substitution. not regex
Set new_dir=!old_dir:%old%=%new%!

endlocal & (
   mycd %new_dir%
)

exit /b 0

:: echo. is to print blank line (empty line)
:usage
   echo.
   echo usage:
   echo.
   echo    %prog% [flags,options] old_pattern new_pattern
   echo.
   echo    this script mimic korn shell's cd command.
   echo.
   echo    -d               debug mode. besically turn on ECHO.
   echo.
   echo example:
   echo.
   echo    tpp3
   echo         this goes to github\tpsup\python3\scripts dir
   echo    %prog% scripts lib   
   echo    %prog% lib     scripts 
   REM this is function return; it doesn't exit the script.
   REM no good way to exit script from inside a function
   exit /b 0

