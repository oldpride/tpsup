@echo off

set YYYYMMDD=%date:~10,4%%date:~4,2%%date:~7,2%

set "USER_TMP=%USERPROFILE%\AppData\Local\Temp"
set "DAILY_TMP=%USER_TMP%\daily\%YYYYMMDD%"

if exist %DAILY_TMP%\ (
   cd %DAILY_TMP%
   exit /b 0
)

cd %USER_TMP%
