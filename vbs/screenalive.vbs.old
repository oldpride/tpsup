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

'https://stackoverflow.com/questions/28765980/vb-script-date-formats-yyyymmddhhmmss
Dim g_oSB : Set g_oSB = CreateObject("System.Text.StringBuilder")

Function sprintf(sFmt, aData)
   g_oSB.AppendFormat_4 sFmt, (aData)
   sprintf = g_oSB.ToString()
   g_oSB.Length = 0
End Function


set wsc = CreateObject("WScript.Shell")
Do
    Dim dt : dt = now()

    willdo = False

    if mode = "worktime" then
       'if (TimeValue("6:20am") <= Time() AND Time() <= TimeValue("3:00pm")) then 
       if (TimeValue("6:20:00") <= Time() AND Time() <= TimeValue("15:00:00")) then 
           'People might forget to switch it off ;)
           WScript.Echo "within worktime"
           willdo = True
       end if 
    elseif mode = "alltime" THEn
       willdo = True
    else
       usage("unsupported mode='" & mode & "'")
    end if

    if willdo Then
        WScript.Echo sprintf("{0:yyyy/MM/dd hh:mm:ss}", Array(dt)) + " click F13 key"

       'F13 key is normally used. therefore, clicking it won't cause side effect
       wsc.SendKeys("{F13}")
    end if

    WScript.Echo sprintf("{0:yyyy/MM/dd hh:mm:ss}", Array(dt)) + " sleep 5 minutes"
    'fIVE MINUTES
    WScript.Sleep(5*60*1000)

Loop
