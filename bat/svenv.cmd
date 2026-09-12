@echo off

if '%1'==''       (
    call addpath -q PATH "%SITEBASE%\Windows\10.0\Chrome\Application"
    call addpath -q PATH "%SITEBASE%\Windows\10.0\chromedriver"
    call "%SITEVENV%\Scripts\activate.bat"
) else (
    @REM check whether the virtual environment exists
    if not exist "%SITEBASE%\github\%1\venv" (
        echo Virtual environment %SITEBASE%\github\%1\venv does not exist
        exit /b 1
    )
    cd "%SITEBASE%\github\%1\venv"
    call "%SITEBASE%\github\%1\venv\Scripts\activate.bat"
)
