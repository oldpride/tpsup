@echo off

if '%1'==''       (
    call addpath -q PATH "%SITEBASE%\Windows\10.0\Chrome\Application"
    call addpath -q PATH "%SITEBASE%\Windows\10.0\chromedriver"
    call "%SITEVENV%\Scripts\activate.bat"
) else (
    @REM check whether the virtual environment exists
    if not exist "%SITEVENV%-%1" (
        echo Virtual environment %SITEVENV%-%1 does not exist
        exit /b 1
    )
    call "%SITEVENV%-%1\Scripts\activate.bat"
)