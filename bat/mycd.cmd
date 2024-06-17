@rem https://superuser.com/questions/129969/navigate-to-previous-directory-in-windows-command-prompt
@echo off
@rem if '%*'=='' cd %userprofile% & exit /b
if '%*'=='' (
    @rem cd /d "%userprofile%" this is not always the home dir
    cd /d "%homedrive%/%homepath%"
    set "OLDPWD=%cd%"
) else if '%*'=='-' (
    @rem ^ is escape char. When variable %OLDPWD% is undefined, it is literal %OLDPWD%
    @rem if NOT '%OLDPWD%' == '^%OLDPWD^%' (
    if defined OLDPWD (
       cd /d "%OLDPWD%"
    ) else (
       echo set OLDPWD=%cd%
    )
    set "OLDPWD=%cd%"
) else (
    cd /d %*
    if not errorlevel 1 (
       set "OLDPWD=%cd%"
    )
)

@rem test
@rem     mycd C:\Program Files\Git
@rem     mycd "C:\Program Files\Git"
@rem     mycd - 
@rem     mycd 
@rem     mycd ..
@rem     mycd C:\Users\william
