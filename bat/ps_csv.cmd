@echo off
REM tasklist /NH | sort
REM 1/19/2024 7:45:23 PM      21160 PowerShell -command "Get-CimInstance -ClassName Win32_Process|Select-object -property CreationDate,ProcessId,CommandLIne| Out-String -Stream -Width 1000" 

REM the following prints full command-line args, better than tasklist
PowerShell -command "(Get-CimInstance -ClassName Win32_Process|Select-object -property CreationDate,ProcessId,CommandLIne|ConvertTo-Csv -NotypeInformation| Out-String)"
