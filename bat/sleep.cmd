@REM sleep specified seconds
@REM usage: sleep 5

set "seconds=%1"

timeout /t %seconds% >nul
