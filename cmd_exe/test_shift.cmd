@echo off
shift
echo arg1 is     shifted: %1
echo arg* is not shifted: %*

setlocal enabledelayedexpansion

set /a idx=0
for %%a in (%*) do (
   set /a "idx+=1"
   if !idx! geq 2 set /p "=%%a "<NUL
)

@echo

exit /b

@echo off
setlocal enabledelayedexpansion

@rem https://stackoverflow.com/questions/15885338/using-batch-file-shift-command
set args=0
for %%I in (%*) do set /a "args+=1"
for /l %%I in (1,1,%args%) do (
    set /a idx=0
    for %%a in (%*) do (
        set /a "idx+=1"
        if !idx! geq %%I set /p "=%%a "<NUL
    )
    echo;
)
