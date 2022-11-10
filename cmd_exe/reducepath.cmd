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


if '%1' == '' (
   echo missing args
   goto :usage
)
   
if NOT '%2' == '' (
   echo more args than expected
   goto :usage
)


set var=%1

:: echo separator=!separator!
:: echo var=!var!

:: https://stackoverflow.com/questions/14879105/windows-path-variable-how-to-split-on-in-cmd-shell-again
:: this page also has how to make PATH unique
::    Summary of steps:
::       - for loop splitting PATH at ';' and properly managing quotes
::          - for loop looking at all previously stored paths
::          - only extend the array if this is a new path to be added
::       - glue the array pack together, clearing the array variable as we go

:: setlocal EnableDelayedExpansion
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

:make_path_unique
  ::setlocal EnableDelayedExpansion
  :: set VNAME=%~1
  :: set VPATH=%~2
  set I=0
  set changed=0
  for %%A in ("%value:;=";"%") do (
    REM :don't use :: as comment in block; otherwise, you will get error: 
    REM :   The system cannot find the drive specified.
    REM :echo A=%%A
    REM :echo I=!I!
    set FOUND=NO
    for /L %%B in (1,1,!I!) do (
        REM :echo B=%%B
        if /I "%%~A"=="!L[%%B]!" set FOUND=YES
    )
    if NO==!FOUND! (
        set /A I+=1
        REM :echo added %%A
        set "L[!I!]=%%~A"
    ) else (
        set /A changed+=1
        if %quiet%==0 (
           echo removed %%A from from %var%
        )
    )
  )
  set "FINAL=!L[1]!"
  for /L %%n in (2,1,!I!) do (
    REM :echo L=!L[%%n]!
    set "FINAL=!FINAL!;!L[%%n]!"

    REM :this following is to clear the temp var. as we had setlocal at beginning, we don't have to do this
    REM :set L[%%n]=   

    REM :echo "FINAL=!FINAL!"
  )
  endlocal & (
    if %changed% == 0 (
       if %quiet% == 0 (
          echo no change in %var%
       )
    )

    if %raw% == 1 (
       REM :set "retval=%FINAL%"
       set "retval=!FINAL!"
       REM :echo %retval% here will not get the new %retval%, only the old %retval% in env.
       REM :we need echo it outside this block. see below
       REM :
       REM :inside (), echo needs double quotes, because %FINAL% could contain () too. for example
       REM :    C:\Program Files (x86)\Common Files\Oracle\Java\javapath
       echo "%FINAL%"
    ) else (
       set "%var%=%FINAL%"
       if %quiet% == 0 (
          echo.
          echo new "%var%=%FINAL%"
          echo.
       )
   )
    )
  )
  exit /b 0

:: echo. is to print blank line (empty line)
:usage
   echo.
   echo usage:   
   echo.
   echo    %prog% [flags,options] var_name 
   echo.
   echo    -d               debug mode. besically turn on ECHO.
   echo    -q               quiet mode, not printing what element is removed. default is to print
   echo    -s string        separator. default to ;. (not implemented yet)
   echo    -r               var_name is actually a raw string 
   echo.
   echo example:
   echo.
   echo    %prog%      PATH 
   echo    %prog% PYTHONPATH 
   echo.
   echo    DON'T Do set test="a;c;b;d;a;b", this makes test equal to "a;c;b;d;a;b", one piece, not
   echo    test equal to a;c;b;d;a;b, 6 pieces
   echo       set "test=a;c;b;d;a;b"
   echo       %prog% test 
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
