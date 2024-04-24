@echo off

setlocal

set "prog=%~nx0"



if "%~1"=="" (
    echo ERROR: wrong number of arguments - missing module name
    goto usage
)

if not "%~2"=="" (
    echo ERROR: wrong number of arguments - too many arguments
    goto usage
)

set "module=%~1"

echo check whether '%module%' is a built-in module
for /f "delims=" %%i in ('node -e "console.log(require.resolve.paths('%module%'))"') do set "result=%%i"
if "%result%"=="null" (
    echo %module% is a built-in module
) else (
    echo %module% is not a built-in module
)

echo.
echo check whether '%module%' is a local module
call npm list %module%

echo.
echo check whether '%module%' is a global module
call npm list -g %module%


echo.
echo search for '%module%' in npm registry
call npm search %module% | findstr /b "%module%"

exit /b 0

:usage
    echo usage:
    echo.
    echo   %prog% module
    echo.
    echo   Find whether a node module is a built-in module or not.
    echo   If it is not a built-in module, then find the path to the module.
    echo   The installation could be global or local.
    echo.
    echo examples:
    echo.
    echo      %prog% http     ^# built-in module
    echo      %prog% ganache  ^# not a built-in module
    echo      %prog% tianjunk ^# none-exist module
    echo.
    exit /b 1

endlocal
