@echo off

:: "   %%~nI        - expands %%I to a file name only "
:: "   %%~xI        - expands %%I to a file extension only "
for /F "delims=" %%I in ("c:\foo\bar baz.txt") do @echo %%~nxI
