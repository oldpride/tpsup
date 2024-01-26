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

Function get_cursor_pos()
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
    cmd = pythonExePath & " " & pythonScriptPath
    WScript.echo cmd

    ' Run the command and capture stdout, stderr, and the exit code
    Dim objExec
    Set objExec = objShell.Exec(cmd)

    ' Read the stdout
    Dim stdout
    stdout = objExec.StdOut.ReadAll()

    return stdout
End Function

    ' 'stdout is like 123,456. assign it to x,y
    ' Dim x, y
    ' x = Split(stdout, ",")(0)
    ' y = Split(stdout, ",")(1)

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

cursor_pos = get_cursor_pos()
old_x = Split(cursor_pos, ",")(0)
old_y = Split(cursor_pos, ",")(1)
WScript.Echo "old_x='" & old_x & "'"
WScript.Echo "old_y='" & old_y & "'"

set wsc = CreateObject("WScript.Shell")
Do
    Dim dt : dt = now()
    HHMM_now = TimeValue(dt)

    if HHMM1 <= HHMM_now AND HHMM_now <= HHMM2 then 
        WScript.Echo sprintf("{0:yyyy/MM/dd hh:mm:ss} ", Array(dt)) & "within (" & HHMM1 & "," & HHMM2 & ") click F13 key"

       'F13 key is normally not used. therefore, clicking it won't cause side effect
       'found side effect of F13 - it changes lower case to upper case
       'To access function keys F13 - F24, press the Shift key in conjunction with function keys F1 - F12
       wsc.SendKeys("{F13}")
    else
        if forever = false then
            WScript.Echo sprintf("{0:yyyy/MM/dd hh:mm:ss} ", Array(dt)) & "outside (" & HHMM1 & "," & HHMM2 & ") exit"
            exit do
        else
            WScript.Echo sprintf("{0:yyyy/MM/dd hh:mm:ss} ", Array(dt)) & "outside (" & HHMM1 & "," & HHMM2 & ") do nothing"
        end if
    end if

    WScript.Echo sprintf("{0:yyyy/MM/dd hh:mm:ss}", Array(dt)) & " sleep 5 minutes"
    'fIVE MINUTES
    WScript.Sleep(5*60*1000)


Loop
