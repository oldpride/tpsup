@echo off

if defined CLASSPATH ( 
   call addpath -p -q PATH "%SITEBASE%\java\lib\antlr-4.9.3-complete.jar"
 ) else (
   set "CLASSPATH=%SITEBASE%\java\lib\antlr-4.9.3-complete.jar"
)


