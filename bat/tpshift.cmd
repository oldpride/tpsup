@echo off

@rem shift %*
@rem    https://stackoverflow.com/questions/15885338/using-batch-file-shift-command

setlocal enabledelayedexpansion
set /a idx=0
for %%a in (%*) do (
   set /a "idx+=1"
   if !idx! geq 2 set /p "=%%a "<NUL
)

@rem echo without extra new line
@rem    https://stackoverflow.com/questions/7105433/windows-batch-echo-without-new-line

@echo;|set /p=
endlocal
