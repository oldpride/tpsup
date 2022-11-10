@echo off

if '%*' == '' (
   cd /D "%HOMEDRIVE%/%HOMEPATH%"
) else if '%*' == 'c' (
   cd /D "C:/Users/%username%"
) else if '%*' == 'up' (
   cd /D "%userprofile%"
) else (
   @rem use %% to escape %
   @rem
   @echo ERROR: unknown usage
   @echo usage: 
   @echo    winhome     - default go to home dir, which is %%HOMEDRIVE%%/%%HOMEPATH%%
   @echo    winhome c   - go to go to /Users/%%username%%, this is not always the home dir
   @echo    winhome up  - go to go to %%USERPROFILE%%,     this is not always the home dir
   exit /b 1
)
