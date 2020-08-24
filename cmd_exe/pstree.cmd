@echo off

setlocal

REM batch script doesn't have a $# equivalent. the following script is the best so far
set argC=0
for %%x in (%*) do Set /A argC+=1
REM echo %argC%


REM batch script has no != operator. use NOT == instead
if %argC% == 0 (
   echo ERROR:   wrong number of args. got %argC%, expected 2. args=%*
   echo usage:   pstree pid
   echo example: pstree 20445
   exit /b
)

set pid=%~1
set level=%~2  

REM increment a variable, /A to indicate it is a number variable
set /A level=level+1

rem
rem windows programming: An A-Z Index of the Windows CMD command line. https://ss64.com/nt/

rem this only gives immediate children
rem    wmic process where (ParentProcessId=%pid%) get Caption,ProcessId
rem example:
rem    > wmic process where (ParentProcessId=20488) get Caption,ProcessId
rem    Caption     ProcessId
rem    chrome.exe  26568
rem    
rem

rem this doesn't work 
rem    FOR /F "tokens=1,2" %%d IN ('wmic process where (ParentProcessId=%pid%) get Caption,ProcessId') DO ...
rem    /F is to loop through each items
rem
rem I had to wrap the command into an external cmd file
rem
rem for wmic command, standard handling including
rem    skip=1" 
rem    findstr /r /v "^$"' 
rem see
rem    https://stackoverflow.com/questions/37706454/skipping-last-empty-line-of-wmic-command-output-in-batch
rem    The wmic command returns Unicode output. Since for /f is not perfect for handling such, it
rem    produces artefacts like orphaned carriage-returns (CR), leading to the effect you encounter
rem    (the last line does not appear empty to your for /f %%i loop as it contains such a CR; remember
rem    that for /f skips lines that are really empty).
rem note to use ^ to escape > and |
rem
FOR /F "tokens=1,2 skip=1" %%d IN ('pschildren %pid% 2^>nul ^| findstr /r /v "^$"') DO  (
   rem %%d is program name, %%e is pid
   echo. level=%level% %%d %%e

   rem must use 'call', otherwise the script will print prompt
   call pstree %%e %level% 
)
endlocal



