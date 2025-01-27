@REM @ver 
@REM Microsoft Windows [Version 10.0.26100.2894] Windows_NT
@REM we extract 10.0 from the output

@echo off

set argC=0
for %%x in (%*) do Set /A argC+=1

for /f "tokens=4 delims=[] " %%i in ('ver') do (
    for /f "tokens=1-2 delims=." %%a in ("%%i") do (
        echo %%a.%%b
    )
)
