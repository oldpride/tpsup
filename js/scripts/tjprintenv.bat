@echo off

:: wrapper script 
:: the original script is tpsup/scripts/cmd_generic.bat.
:: tpsup/scripts/cmd_maker.bash will copy tpsup/scripts/cmd_generic.bat to target's directory
:: and rename it to <target>.bat


set "prog=%~n0"
set "dir=%~dp0"

setlocal enabledelayedexpansion
for %%G in (js ts py) do (
    set "file=%dir%%prog%_cmd.%%G"
    @REM echo "file=!file!"
    
    if exist "!file!" (
        @REM echo "!file! exists"

        @REM if ext is js or ts, use deno
        if "%%G"=="js" (
            call deno run --allow-all "!file!" %*
        ) else if "%%G"=="ts" (
            call deno run --allow-all "!file!" %*
        ) else if "%%G"=="py" (
            call python "!file!" %*
        )
        
        goto :eof
    )
)
endlocal
