@echo off

REM In windows, to unset a var, just set it to nothing
set "USERFULLNAME="

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


if '%2' == '' (
   echo missing args
   goto :usage
)
   
if NOT '%3' == '' (
   echo more args than expected
   goto :usage
)

set cfg=%1
set count=%2

REM before endlocal, use !var_name! to get the new value
REM after endlocal, use %var_name%k

:main
REM start in background
START /b putty -load !cfg!

REM wait for user to pass auth of the first putty.
echo Hit ENTER to continue
pause

REM the rest putty will use the same auth
for /l %%x in (2, 1, !count!) do (
    echo %%x
    START /b putty -load !cfg!
    REM sleep 1 second
    timeout /t 1
)

endlocal & set "USERFULLNAME=%DisplayName%"
  
exit /b 0

:: echo. is to print blank line (empty line)
:usage
   echo.
   echo usage:   
   echo.
   echo    %prog% config count
   echo.
   echo    start putty with config for count times
   echo.
   echo    prep work: 
   echo            in the config: Connection: SSH, 
   echo            enable "share SSH connections if possible"
   echo. 
   echo    -d               debug mode. besically turn on ECHO.
   echo.       
   echo.
   echo example:
   echo.
   echo    %prog% myappdev1 10
   echo.

   REM this is function return; it doesn't exit the script.
   REM no good way to exit script from inside a function
   exit /b 1