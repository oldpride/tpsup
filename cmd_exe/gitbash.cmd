@echo off
@REM there are a few bash.exe in the system, we need to use the one from git
@REM C:\Windows\System32\bash.exe is for WSL
"C:/Program Files/Git/bin/bash.exe" %*
