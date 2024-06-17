@echo off

:: setlocal can be nested
setlocal EnableDelayedExpansion
:: when EnableDelayedExpansion is set, %var% becomes !var!, except in IF's condition part.
::    

:: ways to parse optional args
:: https://stackoverflow.com/questions/3973824/windows-bat-file-optional-argument-parsing
::
set "prog=%~n0"
set separator=;
set quiet=0
set raw=0
:check_optional
   :: shift doesn't work in a block, eg, in a if-block, therefore move it to outside
   :: https://stackoverflow.com/questions/17241184/windows-batch-shift-not-working-in-if-block
   set check_again=0
   if '%1'=='-d'       (
      @echo on
      set check_again=1
      goto :shift_once
   )
   if '%1'=='-r'       (
      set raw=1
      set check_again=1
      goto :shift_once
   )
   if '%1'=='-q'       (
      set quiet=1
      set check_again=1
      goto :shift_once
   )
   if '%1'=='-s'       ( 
      set separator=%2
      if not defined separator (
          echo option requires an argument -- 's'
          goto :usage
      )
      set check_again=1
      goto :shift_twice
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


set var=%1
set pattern=%2

REM before endlocal, use !var_name! to get the new value
REM after endlocal, use %var_name%

if !raw! == 1 (
   set value=!var!
   REM remove double quotes. if without EnableDelayedExpansion, this would be
   REM    set value=%value:"=%
   REM now that we have EnableDelayedExpansion, we use
   set value=!value:"=!
   set var=raw
) else (
   set value=!%var%!

   if NOT defined !var! (
      echo !var! is undefined.
      exit /b 0
   )

   if %quiet% == 0 (
      echo old "%var%=!value!"
      echo.
   )
)

:: echo value=!value!

REM use double quotes to avoid error when value contains (). for example
REM    C:\Program Files (x86)\Common Files\Oracle\Java\javapath

:delpath
  ::setlocal EnableDelayedExpansion
  set changed=0
  for %%i in ("%value:;="; "%") do (
    REM :don't use :: as comment in block; otherwise, you will get error: 
    REM :   The system cannot find the drive specified.

    REM: 1. 
    REM: echo with arg will turn on/off echo.
    REM: echo. will print a blank line. in case %%~i is empty, we print blank line.
    REM: 2.
    REM: ~ in %%~i will remove double quotes. 
    REM: echo. "%%~i"
    REM: 3.
    REM: semi-regex pattern matching, findstr /r /i "!pattern!">nul 2>&1
    REM:    see https://stackoverflow.com/questions/34524390
    REM:    findstr has no full REGEX Support. Especially no {Count}
    echo. "%%~i" | findstr /r /i "!pattern!">nul 2>&1
    if errorlevel 1 (
        REM not matched, keep it
        if "!FINAL!" == "" (
            set "FINAL=%%~i"
        ) else (
            set "FINAL=!FINAL!!separator!%%~i"
        )
    ) else (
        REM matched
        echo dropped "%%~i"
    )
  )

   REM echo "FINAL=!FINAL!"

endlocal & (
    REM before endlocal, use !var_name!
    REM after endlocal, use %var_name%
    
    if %quiet% == 0 (
        echo new "%var%=%FINAL%"
    )

    REM use double quotes to avoid error when value contains (). for example
    REM    C:\Program Files (x86)\Common Files\Oracle\Java\javapath
    if "%value%" == "%FINAL%" (
       if %quiet% == 0 (
          echo no change in %var%
       )
    ) else (
        if %raw% == 1 (
            REM :set "retval=%FINAL%"
            REM :echo %retval% here will not get the new %retval%, only the old %retval% in env.
            REM :we need echo it outside this block. see below
            REM :
            REM :inside (), echo needs double quotes, because %FINAL% could contain () too. for example
            REM :    C:\Program Files (x86)\Common Files\Oracle\Java\javapath
            echo "%FINAL%"
        ) else (
            set "%var%=%FINAL%"
        )
    )    
)
exit /b 0

:: echo. is to print blank line (empty line)
:usage
   echo.
   echo usage:   
   echo.
   echo    %prog% [flags,options] var_name pattern
   echo.
   echo    -d               debug mode. besically turn on ECHO.
   echo    -q               quiet mode, not printing what element is removed. default is to print
   echo    -s string        separator. default to ;. (not implemented yet)
   echo    -r               var_name is actually a raw string 
   echo.
   echo example:
   echo.
   echo    %prog%       PATH code
   echo    %prog% PYTHONPATH code
   echo.
   echo    DON'T Do 
   echo       set test="a;c;b;d;a;b", 
   echo    this makes test equal to "a;c;b;d;a;b", one piece,
   echo    DO the following to set test equal to a;c;b;d;a;b, 6 pieces
   echo       set "test=a;c;b1;d;a;b2"
   echo       %prog% test b
   echo       echo %%test%%
   echo    in one line:
   :: https://stackoverflow.com/questions/29814241/windows-batch-echo-variable-with-old-value
   :: when running multiple commands in one line, the commands are all first parsed
   ::    set x=a
   ::    set x=b & echo %x%
   :: you will see
   ::    a
   :: because %x% at parse time is a
   :: in order to get b
   :: you need to do
   ::    set x=b & call echo ^%x^%
   :: this forces %x% is resolved in run-time
   :: note:
   ::    below, use ^ to escape ^ and &. use % to escape %
   echo       set "test=a a;a c;a d;a b;a a;a b" ^& %prog% test ^& call echo ^^%%test^^%%
   echo    we should see 
   echo       a a;a c;a d;a b
   echo.
   echo    %prog% -r "a a;a c;a d;a b;a a;a b"
   echo    we should see
   echo       a a;a c;a d;a b
   echo.
   echo note: in batch, only double quotes can group; single quotes cannot.

   REM this is function return; it doesn't exit the script.
   REM no good way to exit script from inside a function
   exit /b 0
