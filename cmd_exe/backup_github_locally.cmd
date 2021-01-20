REM @echo off


set yyyymmdd=%date:~10,4%%date:~7,2%%date:~4,2%

set "source=C:\users\william\sitebase\github"

set "backup_base=F:\backup\"
set "backup_dir=%backup_base%\%yyyymmdd%\github\"

xcopy "%source%" "%backup_dir%" /s /e /y || goto :error

cd /D "%backup_base%" || goto :error
REM https://stackoverflow.com/questions/5497211/batch-file-to-delete-folders-older-than-10-days-in-windows-7
REM FORFILES /D -20 /M 20* /C "cmd /c echo @path"
    FORFILES /D -20 /M 20* /C "cmd /c rd /S /Q @path"

REM sleep a little so that user can see the output
timeout /t 60
exit /b

REM Let BATCH abort on error
REM https://stackoverflow.com/questions/734598/how-do-i-make-a-batch-file-terminate-upon-encountering-an-error
:error
echo Failed with error #%errorlevel%.
REM sleep a little so that user can see the output
timeout /t 60
exit /b %errorlevel%
