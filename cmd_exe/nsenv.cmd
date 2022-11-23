:: NativeScript env
::
@echo off

:: set JAVA_HOME to jdk11
call java11.cmd

:: add path for keytool.exe
call addpath -q PATH "%JAVA_HOME%\bin"
