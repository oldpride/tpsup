@echo off

setlocal EnableDelayedExpansion
set "prog=%~n0"

REM i cannot run a command with wildcard. so I use the following to resolve wildcard first.
REM https://stackoverflow.com/questions/25794369
for /d %%a in ("C:\Users\%USERNAME%\apache-maven-*") do (
   set "mavendir=%%~fa"
)
REM echo %mavendir%

endlocal & (
   if "%mavendir%"=="" (
      echo "C:\Users\%USERNAME%\apache-maven-* not found"
      exit /b
   ) else (
      call %mavendir%\bin\mvn.cmd %*
   )
)

