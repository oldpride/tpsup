@echo off

:: wrapper script 

:: this script is created (copied) from ptgeneric_make_cfg_exec.bash
:: see tpsup/python3/scripts/Makefile


set "prog=%~n0"
set "dir=%~dp0"

set "types=batch trace"
set "seen_type="
for %%i in (%types%) do (
   if exist "%dir%\%prog%_cfg_%%i.py" (
      if defined seen_type (
         echo "ERROR: found multiple cfg files for %prog%: %seen_type% and %%i"
          exit /b 1
      ) else (
         set "seen_type=%%i"
      )
   )
)

if not defined seen_type (
   echo "ERROR: no cfg file found for %prog%: missing %dir%\%prog%_cfg_<type>.py"
    exit /b 1
)

set "type=%seen_type%"

@REM unset seen_type
set "seen_type="

@REM save prog, type as they be overridden by p3env and svenv
@REM somehow the pair of save and restore has to be outside the IF block
set "saved_prog=%prog%"
set "saved_type=%type%"

@REM if VIRTUAL_ENV is not set, set env
if not defined VIRTUAL_ENV (
    call p3env
    call svenv
)

@REM restore prog, type
set "prog=%saved_prog%"
set "type=%saved_type%"

set "cfg=%dir%\%prog%_cfg_%type%.py"
set "pyfile=%TPSUp%/python3/scripts/pt%type%.py"

@REM remove /cygdrive/c in the pyfile
@REM    eg, C:\cygdrive\c/Users/tian/sitebase/github/tpsup/python3/scripts/ptbatch.py
set "pyfile=%pyfile:/cygdrive/c/=C:/%"
set "pyfile=%pyfile:cygdrive\c=%"
python "%pyfile%" "%cfg%" -c "%prog%" %*
