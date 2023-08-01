@echo off

:: wrapper script 


set "prog=%~n0"
set "dir=%~dp0"

set "cfg=%dir%/%prog%_cfg_batch.py"
python "%TPSUp%/python3/scripts/tpbatch.py" "%cfg%" -c "%prog%" %*
