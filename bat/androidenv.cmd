:: Android Studio env
::
@echo off

rem call addpath -q PATH "%ANDROID_HOME%\tools\bin;%ANDROID_HOME%\platform-tools;%ANDROID_HOME%\build-tools\33.0.0;%ANDROID_HOME%\emulator"

rem find the latest build-tools
for /f "tokens=*" %%a in ('dir /b /ad /o-n "%ANDROID_HOME%\build-tools"') do (
  set ANDROID_BUILD_TOOLS=%%a
  goto :break
)
:break

rem set the path
call addpath -q PATH "%ANDROID_HOME%\cmdline-tools\latest\bin;%ANDROID_HOME%\platform-tools;%ANDROID_HOME%\build-tools\%ANDROID_BUILD_TOOLS%;%ANDROID_HOME%\emulator"
