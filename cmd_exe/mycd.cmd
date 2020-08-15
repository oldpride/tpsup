@rem https://superuser.com/questions/129969/navigate-to-previous-directory-in-windows-command-prompt
@echo off
@rem if '%*'=='' cd %userprofile% & exit /b
if '%*'=='' (
    cd /d %userprofile%
    set OLDPWD=%cd%
) else if '%*'=='-' (
    @rem ^ is escape char. When variable %OLDPWD% is undefined, it is literal %OLDPWD%
    if NOT '%OLDPWD%' == '^%OLDPWD^%' (
       cd /d %OLDPWD%
    ) else (
       echo set OLDPWD=%cd%
    )
    set OLDPWD=%cd%
) else (
    cd /d %*
    if not errorlevel 1 (
       set OLDPWD=%cd%
    )
)
