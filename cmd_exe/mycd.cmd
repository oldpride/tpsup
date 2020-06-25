@rem https://superuser.com/questions/129969/navigate-to-previous-directory-in-windows-command-prompt
@echo off
rem if '%*'=='' cd %userprofile% & exit /b
if '%*'=='' (
    cd /d %userprofile%
    set OLDPWD=%cd%
) else if '%*'=='-' (
    cd /d %OLDPWD%
    set OLDPWD=%cd%
) else (
    cd /d %*
    if not errorlevel 1 set OLDPWD=%cd%
)
