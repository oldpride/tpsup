@echo off

:: wrapper script 


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
   echo "ERROR: no cfg file found for %prog%"
    exit /b 1
)

set "type=%seen_type%"

set "cfg=%dir%/%prog%_cfg_%type%.py"
python "%TPSUp%/python3/scripts/pt%type%.py" "%cfg%" -c "%prog%" %*


