'this will keep Skype status green without admin access
'   https://gist.github.com/lkannan/23bb39fe4938485f775221ff35148757

'to run from cmd.exe/cygwin/gitbash
'   cscript screenalive.vbs

Function usage(msg)
    WScript.Echo msg 
    WScript.Echo ""
    WScript.Echo "Usage:"
    WScript.Echo "       cscript screenalive.vbs  alltime"
    WScript.Echo "       cscript screenalive.vbs worktime"
    WScript.Echo "       cscript screenalive.vbs 30"
    WScript.Echo "               integer is the number of minutes to live"
    WScript.Echo ""
    WScript.Quit(1) 
    'If calling a VBScript from a batch file, catch the Errorlevel with an IF statement
    '   cscript.exe MyScript.vbs
    '   IF errorlevel 1 goto s_next
end Function

if WScript.Arguments.Count = 0 then
    usage("ERROR: Missing parameters")
end if

mode = WScript.Arguments.Item(0)
WScript.Echo "mode='" & mode & "'"

'whether to run forever
forever = false

'https://stackoverflow.com/questions/28765980/vb-script-date-formats-yyyymmddhhmmss
Dim g_oSB : Set g_oSB = CreateObject("System.Text.StringBuilder")

Function sprintf(sFmt, aData)
   g_oSB.AppendFormat_4 sFmt, (aData)
   sprintf = g_oSB.ToString()
   g_oSB.Length = 0
End Function

Dim objShell
Set objShell = WScript.CreateObject("WScript.Shell")

' Specify the path to your Python interpreter and script
Dim pythonExePath
' pythonExePath = "C:\Python\python.exe"
' use the python in PATH
pythonExePath = "python"

cmd = "where " & pythonExePath
WScript.echo "cmd = " & cmd
Dim objExec
Set objExec = objShell.Exec(cmd)
Dim stdout
stdout = objExec.StdOut.ReadAll()
WScript.echo "python path = " & stdout

Dim pythonScriptPath
' pythonScriptPath = "C:\path\to\your\python\script.py"
'script path uses environment variable
pythonScriptPath = "%TPSUP%\python3\scripts\get_cursor_pos.py"

'resolve environment variables
pythonScriptPath = objShell.ExpandEnvironmentStrings(pythonScriptPath)

WScript.echo "script path =" & pythonScriptPath

'check whether the script exists
Dim fso
Set fso = CreateObject("Scripting.FileSystemObject")
Dim has_script
has_script = fso.FileExists(pythonScriptPath)
if has_script = false then
    WScript.echo "ERROR: python script '" & pythonScriptPath & "' does not exist"
    'return value by assigning to function name
end if

Dim cmd
' cmd = pythonExePath & " " & pythonScriptPath
' wrap the path in double quotes in case it contains spaces
' in vbscript, double quotes are escaped by double double quotes
cmd = """" & pythonExePath & """" & " " & """" & pythonScriptPath & """"

WScript.echo "cmd = " & cmd

Function get_cursor_pos()
    if has_script = false then
        get_cursor_pos = ""
    else
        ' Run the command and capture stdout, stderr, and the exit code
        Dim objExec
        Set objExec = objShell.Exec(cmd)

        ' Read the stdout
        Dim stdout
        stdout = objExec.StdOut.ReadAll()

        ' remove the trailing newline
        stdout = Replace(stdout, vbCrLf, "")

        'return value by assigning to function name
        get_cursor_pos = stdout
    end if
End Function

if mode = "worktime" then
    HHMM1 = TimeValue("6:20am")
    HHMM2 = TimeValue("3:00pm")
    forever = true
elseif mode = "alltime" then
    HHMM1 = TimeValue("00:01am")
    HHMM2 = TimeValue("11:59pm")
    forever = true
elseif isNumeric(mode) then
    'if mode is an integer, then it is the number of minutes
    'add the number of minutes to the current time
    HHMM1 = TimeValue(now())
    HHMM2 = TimeValue(now() + mode/24/60)
else
    usage("unsupported mode='" & mode & "'")
end if

if HHMM1 > HHMM2 then
    'time wrapped around, likely over midnight. set HHMM2 to midnight
    HHMM2 = TimeValue("11:59pm")
    WScript.Echo "HHMM1 > HHMM2, set HHMM2 to midnight"
end if

WScript.Echo "HHMM1='" & HHMM1 & "'"
WScript.Echo "HHMM2='" & HHMM2 & "'"

'save the current cursor position
Dim cursor_pos
cursor_pos_old = get_cursor_pos()
WScript.Echo "cursor_pos_old='" & cursor_pos_old & "'"

Dim dt : dt = now()
HHMM_now = TimeValue(dt)

set wsc = CreateObject("WScript.Shell")
Do
    WScript.Echo sprintf("{0:yyyy/MM/dd hh:mm:ss}", Array(dt)) & " sleep 5 minutes"
    'FIVE MINUTES
    WScript.Sleep(1*60*1000)

    dt = now()
    HHMM_now = TimeValue(dt)

    if HHMM1 <= HHMM_now AND HHMM_now <= HHMM2 then 
        WScript.Echo sprintf("{0:yyyy/MM/dd hh:mm:ss} ", Array(dt)) & "within (" & HHMM1 & "," & HHMM2 & ") click F13 key"

       'check whether the cursor position has changed.
        '  if it has not changed, then click F13 key
        'F13 key is normally not used.
        'found side effect of F13 - it changes lower case to upper case. therefore, avoid using it if possible.
        'To access function keys F13 - F24, press the Shift key in conjunction with function keys F1 - F12.
        Dim cursor_pos_now
        cursor_pos_now = get_cursor_pos()
        WScript.Echo "cursor_pos_now='" & cursor_pos_now & "'"
        if cursor_pos_now = cursor_pos_old then
            WScript.Echo "cursor_pos_now='" & cursor_pos_now & "' is the same as cursor_pos_old='" & cursor_pos_old & "', click F13 key"
            wsc.SendKeys("{F13}")
        else
            WScript.Echo "cursor_pos_now='" & cursor_pos_now & "' is different from cursor_pos_old='" & cursor_pos_old & "', do nothing"
        end if
        cursor_pos_old = cursor_pos_now
    else
        if forever = false then
            WScript.Echo sprintf("{0:yyyy/MM/dd hh:mm:ss} ", Array(dt)) & "outside (" & HHMM1 & "," & HHMM2 & ") exit"
            exit do
        else
            WScript.Echo sprintf("{0:yyyy/MM/dd hh:mm:ss} ", Array(dt)) & "outside (" & HHMM1 & "," & HHMM2 & ") do nothing"
        end if
    end if



Loop
