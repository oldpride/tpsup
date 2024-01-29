@echo off

setlocal EnableDelayedExpansion

if 2 == 2 (
    if exist c:\ (
        set "testvar=1"
        echo testvar1.1=!testvar!
    )

    echo testvar1.2=!testvar!

    @REM how do we check if a variable is set?
    if defined testvar (
        echo testvar is defined
        echo testvar1.3=!testvar!
    ) else (
        echo testvar is not defined
    )
)

@REM this is set
echo testvar2=!testvar!

@REM pass the value to the parent environment
endlocal & set "testvar=%testvar%"

echo testvar3=%testvar%

set "testvar="
