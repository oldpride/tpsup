@echo off

:: basename
set "prog=%~n0"

if NOT DEFINED MYBASE set "MYBASE=%SITEBASE%
echo MYBASE=%MYBASE%

:: https://stackoverflow.com/questions/636381/what-is-the-best-way-to-do-a-substring-in-a-batch-file
if '%prog:~0,4%'=='mysite' (
   set "suffix=%prog:~4,20%"

   @cd "%MYBASE%/github/tpsup/scripts"

   exit /b 0
) 

if '%prog:~0,2%'=='my' (
   set "suffix=%prog:~2,20%"

   if '%suffix%'=='ps3' ( 
      cd "%MYBASE%/github/tpsup/python3/scripts"
   )
   exit /b 0
) 
