@REM we need to use full path of tpbash.cmd when called from 'sudo',
@REM therefore, get the dir of this script
@set "dir=%~dp0"
@call "%dir%/tpbash.cmd" wsl %*
