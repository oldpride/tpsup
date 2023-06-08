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


if '%2' == '' (
   echo missing args
   goto :usage
)
   
if NOT '%3' == '' (
   echo more args than expected
   goto :usage
)


set way=%1
set user1=%2

REM before endlocal, use !var_name! to get the new value
REM after endlocal, use %var_name%k

:main
if "!way!" == "user" (
    REM use ^ to escape | in the loop's command
    REM Full Name                John Smith
    REM tokens=2* means get 2nd and all tokens, assign to %%b.
    for /f "tokens=2*" %%a in ('net user "%user1%" ^| find /i "Full Name"') do set DisplayName=%%b
    echo. !DisplayName!
) else if "!way!" == "domain" (
    REM use ^ to escape | in the loop's command
    REM Full Name                John Smith
    REM tokens=2* means get 2nd and all tokens, assign to %%b.
    for /f "tokens=2*" %%a in ('net user "%user1%" /domain ^| find /i "Full Name"') do set DisplayName=%%b
    echo. !DisplayName!
) else if "!way!" == "wmic" (
    REM use ^ to escape | in the loop's command
    REM FullName=John Smith
    REM tokens=2 means get 2nd token, assign to %%a.
    REM delims== means use = as delimiter
    for /f "tokens=2 delims==" %%a in ('wmic useraccount where name^="%user1%" get fullname /value ^| find /i "FullName"') do set DisplayName=%%a
    echo. !DisplayName!
) else (
    echo "unknown way=%way%"
    goto :usage
)

endlocal & set "USERFULLNAME=%DisplayName%"
  
exit /b 0

:: echo. is to print blank line (empty line)
:usage
   echo.
   echo usage:   
   echo.
   echo    %prog% [flags,options] query_way username
   echo.
   echo    -d               debug mode. besically turn on ECHO.
   echo    query_way        
   echo              'user' - net user username. fast.
   echo              'domain' - net user username /domain. fast.
   echo              'wmic' - wmic useraccount where name="username". slow.
   echo.
   echo example:
   echo.
   echo    %prog% user   %USERNAME%
   echo    %prog% domain %USERNAME%
   echo    %prog% wmic   %USERNAME%
   echo.

   REM this is function return; it doesn't exit the script.
   REM no good way to exit script from inside a function
   exit /b 1
