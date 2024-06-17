@echo off
rem C:\cygwin64\bin\cygpath.exe -w "/home/%USERNAME%"
rem
rem how to assign cmd output to variable
rem
rem https://stackoverflow.com/questions/2323292/assign-output-of-a-program-to-a-variable-using-a-ms-batch-file
rem 
rem the first % is to escape the second %

for /f %%i in ('C:\cygwin64\bin\cygpath.exe -w "/home/%USERNAME%"') do set "CYGHOME=%%i"
cd "%CYGHOME%"

