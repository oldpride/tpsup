@echo off

set "prog=%~n0"

if "%1"=="" goto usage

set "match_pattern=0"
set "debug_me=0"

:check_optional
   set check_again=0
   if '%1'=='-d'       (
        @echo on
        set "debug_me=1"
        set check_again=1
        goto :shift_once
    )

    if '%1'=='-p'       (
        set "match_pattern=1"
        set check_again=1
        goto :shift_once
    )
    if %check_again% == 0 goto :finished_optional
:shift_once
shift
goto :check_optional
:finished_optional

if "%1"=="" goto usage

@REM echo %*

if %match_pattern% == 1 (
    @REM echo match pattern

    for %%x in (%*) do (
        @REM if-continue pattern in batch file.
        @REM goto :Label inside of a block of code () like a for loop breaks the block context
        @REM https://stackoverflow.com/questions/36355490
        call :HANDLE_PATTERN %%x
    )
)  else (
    for %%x in (%*) do (
        call :HANDLE_VAR %%x
    )
)
exit /b 0

:HANDLE_PATTERN env_var_pattern
    set "pattern=%~1"
    if "%pattern%"=="-p" (
        goto :CONTINUE
    ) 
    if "%pattern%"=="-d" (
        goto :CONTINUE
    )

    @REM the following part is too noisy during debug. we turn it off temporarily even if debug_me is on.
    @echo off
    for /f "delims==" %%v in ('set') do (
        @REM echo parsing %%v
        set "var=%%v"

        echo. "%%~v" | findstr /r /i "%pattern%">nul 2>&1
        if errorlevel 1 (
            @REM not matched, keep it
        ) else (
            @REM matched
            echo unsetting %%v
            set "%%v="
        )
    )
    if %debug_me% == 1 (
        @echo on
    )
    :CONTINUE
    exit /b

:HANDLE_VAR env_var
    set "env_var=%~1"

    if "%env_var%"=="-d" (
        goto :CONTINUE
    ) 

    @REM check env_var is defined
    if not defined %env_var% (
        goto :CONTINUE
    )
    echo unsetting %env_var%
    set "%env_var%="
    
    :CONTINUE
    exit /b

@REM : echo. is to print blank line (empty line)
:usage
   echo.
   echo usage:   
   echo.
   echo    %prog% [flags] var_pattern
   echo.
   echo.       -d              debug flag
   echo.       -p              match pattern
   echo.
   echo example:
   echo.
   echo    %prog% -p SITE TPSUP
   echo.
   echo    %prog% SITEBASE TPSUP
   echo.


   @REM this is function return; it doesn't exit the script.
   @REM no good way to exit script from inside a function
   exit /b 0
:eof
