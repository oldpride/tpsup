Dim objShell
Set objShell = WScript.CreateObject("WScript.Shell")

' Specify the path to your Python interpreter and script
Dim pythonExePath
' pythonExePath = "C:\Python\python.exe"
' use the python in PATH
pythonExePath = "python"

Dim pythonScriptPath
' pythonScriptPath = "C:\path\to\your\python\script.py"
'script path uses environment variable
pythonScriptPath = "%TPSUP%\python3\scripts\get_cursor_pos.py"
WScript.echo pythonScriptPath

Dim cmd
cmd = pythonExePath & " " & pythonScriptPath & " " & "arg1 arg2"
WScript.echo cmd

' Run the command and capture stdout, stderr, and the exit code
Dim objExec
Set objExec = objShell.Exec(cmd)

' Read the stdout
Dim stdout
stdout = objExec.StdOut.ReadAll()

' Read the stderr
Dim stderr
stderr = objExec.StdErr.ReadAll()

' Get the exit code
Dim exitCode
exitCode = objExec.ExitCode

' Display the output
WScript.Echo "stdout: " & stdout
WScript.Echo "stderr: " & stderr
WScript.Echo "exit code: " & exitCode

'stdout is like 123,456. assign it to x,y
Dim x, y
x = Split(stdout, ",")(0)
y = Split(stdout, ",")(1)
' x, y = Split(stdout, ",")

WScript.Echo "x: " & x
WScript.Echo "y: " & y


      
    