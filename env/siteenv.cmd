@echo off
rem set up a link under user home dir
rem    run cmd.exe as administrator
rem    cd C:\Users\william
rem    C:\Users\william>mklink siteenv.cmd sitebase\github\tpsup\env\siteenv.cmd
rem    symbolic link created for siteenv.cmd <<===>> sitebase\github\tpsup\env\siteenv.cmd

set PATH=%PATH%;%userprofile%/sitebase/github/tpsup/cmd_exe
tpsup

