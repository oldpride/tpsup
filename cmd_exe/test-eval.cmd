rem @ECHO OFF
SET a=path
SET b=abc
SETLOCAL EnableDelayedExpansion
echo !%a%!
echo "!%a%!"
echo "%%a%%"
set "value=!%a%!"
rem set "%b%=!%a%!"
set "%b%=%value%"
echo abc=%abc%
endlocal & (
   set "%b%=%value%"
)
echo abc=%abc%
