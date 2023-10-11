echo off
REM change back slash to forward slash
REM change \ to /
REM change \a\b to /a/b


set "v1=\a\b"
set "v2=%v1:\=/%"

echo v1=%v1%
echo v2=%v2%

set "HOME=%USERPROFILE:\=/%"
echo %USERPROFILE%
echo %HOME%

