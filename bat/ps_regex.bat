@echo off

:: wrapper script 

:: this script is created (copied) from ptgeneric_make_cfg_exec.bash
:: see tpsup/python3/scripts/Makefile


set "prog=%~n0"
set "dir=%~dp0"


set "script_ps1=%dir%/../ps1/%prog%.ps1"

powershell -ExecutionPolicy Bypass -File "%script_ps1%" %*
