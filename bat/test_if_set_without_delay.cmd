@echo off
if 2 == 2 (
    if exist c:\ (set "test_var=1")

    @REM this is not set
    echo test_var1=%test_var%

    @REM how do we check if a variable is set?
    if defined test_var (
        echo test_var is defined
        echo test_var1.1=%test_var%
        echo value not seen because it was resolved when the if block was entered (parsed).
        echo solution: to get real-time value, use delayed expansion.
        echo see https://stackoverflow.com/questions/42283939
    ) else (
        echo test_var is not defined
    )
)

@REM this is set
echo test_var2=%test_var%

set "test_var="
