@echo off

setlocal

REM batch script doesn't have a $# equivalent. the following script is the best so far
set argC=0
for %%x in (%*) do Set /A argC+=1
REM echo %argC%


REM batch script has no != operator. use NOT == instead
REM echo. is to print a blank line
if %argC% == 0 (
   echo ERROR:   wrong number of args. got %argC%, expected 1. args=%*
   echo usage:   
   echo.    
   echo    cmd.exe:        pkill     pattern
   echo                    pkill     chromedriver
   echo.
   echo    cygwin/gitbash: pkill.cmd pattern
   echo                    pkill.cmd chromedriver
   echo.
   echo    This script kills child processes too. 
   echo    For example, "pkill chromedriver" will kill also chrome.exe sprawned by chromedriver.
   echo.
   exit /b
)

set pattern=%1

rem from tasklist /NH
rem    browser_broker.exe           27816 Console                    1      7,896 K

rem this is the short working version
rem    use ^ to escape | in the loop's command
rem    windows loop variable can only be single letter
rem    FOR /F "tokens=2" %%p IN ('tasklist /NH ^| findstr "%pattern%"') DO kill %%p


rem more about for loop. example
rem    for /f "tokens=1,2,3,4,5 delims=;+" %%G in ('type filename.txt') do echo %%G %%H %%K
rem
rem    You can use almost any character as a delimiter, but they are case sensitive.
rem    If you don't specify delims it will default to "delims=<tab><space>"
rem 
rem    delims should always the last item in the options string "tokens=3 delims= " not "delims=  tokens=3"
rem    This is because the quotations around the options string do double duty as a terminator for the
rem    delims character(s), which is particularly important when that character is a space.
rem 
rem    You can remove all delimiters by using "delims=" this will place everything on the line into the
rem    first token.
rem 
rem    One special case is using a quote (") as delimiter.
rem    By default this will be seen as the end of the "delims string" unless all the outer enclosing
rem    quotes are removed and all delimiter chars are instead escaped with ^.
rem
rem    Each token specified will cause a corresponding parameter letter to be allocated. The letters used
rem    for tokens are case sensitive.
rem 
rem    If the last character in the tokens= string is an asterisk, then additional parameters are 
rem    allocated for all the remaining text on the line.
rem    therefore, if you start with letter %%p, then next token will go to %%q, and then %%r

@REM FOR /F "tokens=1,2,3 delims=," %%a IN ('tasklist /NH /FO CSV ^| findstr /i "%pattern%"') DO (
@REM    rem from tasklist /NH
@REM    rem    browser_broker.exe           27816 Console                    1      7,896 K
@REM    rem use /FO CSV to handle csv space inside command name
@REM    rem    "Appium Inspector.exe" "1760" "Console"
  
@REM    rem %%a is program name
@REM    rem %%b is pid
@REM    rem %%c is Console or Service
@REM    echo killing %%a %%b %%c and its children


FOR /F "tokens=1,2,3 delims=," %%a IN ('ps_csv.cmd ^| findstr /i %pattern%') DO (
   @REM ps_csv.cmd  this prints full command-line args, better than tasklist  
   @REM 1/24/2025 11:57:28 AM     15300 python  -m http.server 8000
   @REM 1/24/2025 12:53:32 PM      2948 C:\Windows\system32\cmd.exe  /S /D /c" grep http.server"
  
   rem %%a is datetime
   rem %%b is pid
   rem %%c is Command-line args
   echo killing %%a %%b %%c and its children

   rem echo immediate child processes:
   rem wmic process where (ParentProcessId=%b) get Caption,ProcessId 
   rem wmic process where (ParentProcessId=20488) get Caption,ProcessId
   rem Caption     ProcessId
   rem chrome.exe  26568
   
   rem use pstree.cmd instead of pstree, so that we can also run this from cygwin and gitbash
   call pstree.cmd %%b

   taskkill /F /PID %%b /T

   rem /F     force
   rem /PID   kill by PID
   rem /T     also kill child processes 
)

endlocal
