<#
   To run from cmd.exe, powershell, Cygwin:
   powershell -ExecutionPolicy Bypass -File ./tpnc.ps1 -v localhost 5555

   To see help message
   powershell -ExecutionPolicy Bypass -File ./tpnc.ps1 -?
   tpnc.ps1 [-remote_host] <string> [-remote_port] <string> [-v] [<CommonParameters>]
#>

[CmdletBinding(PositionalBinding = $false)]

param(
    [switch]$v = $false,
    [string]$l = $null,
    [string]$infile = $null,
    [string]$outfile = $null,
    [Parameter(ValueFromRemainingArguments = $true)] $remainingArgs = $null
)

Set-StrictMode -Version Latest
#Set-PsDebug -Trace 1

if ($v) {
    $verbosePreference = "Continue"
}

Write-Verbose "verbose=$v"
Write-Verbose "listener=$l"
Write-Verbose "remainingArgs=$remainingArgs"
if ($remainingArgs) {
    Write-Verbose "remainingArgs size=$($remainingArgs.count)"
}

function usage {
    param([string]$message = $null)

    if ($message) {
        Write-Host $message
    }

    Write-Host "
Usage:

  Netcat in powershell

  as a server
     tpnc -l listener_port

  as a client
     tpnc remote_host remote_port

  -v                  verbose mode.

  -infile path        input from this file. default is stdin.
                      powershell doesn't support redirect of stdin '<'. To redirect, use this switch.

  -outfile path       output to this file. default is stdout.
                      powershell's '>' doesn't support binary output because powershell
                      interprets control characters. To save binary output, use this switch.

Examples:

  as a server
     powershell -ExecutionPolicy Bypass -File ./tpnc.ps1 -l 5555

  as a client
     powershell -ExecutionPolicy Bypass -File ./tpnc.ps1 localhost 5555

  to transfer binary file. this is best way preserve the content.
     on server side: 
        powershell -ExecutionPolicy Bypass -File ./tpnc.ps1 -infile  `$env:WINDIR\System32\xcopy.exe -v -l 5555

     on client side:
        powershell -ExecutionPolicy Bypass -File ./tpnc.ps1 -outfile `$env:USERPROFILE\Downloads\output.bin -v localhost 5555

     in cygwin to run cksum or cmp check results
        
        cksum /cygdrive/c/Windows/System32/xcopy.exe /cygdrive/c/users/`$USER/downloads/output.bin
        cmp   /cygdrive/c/Windows/System32/xcopy.exe /cygdrive/c/users/`$USER/downloads/output.bin

"

    exit 1
}

$hasConsole = $true
try {
    [Console]::KeyAvailable | Out-Null
}
catch [System.InvalidOperationException]{
    $hasConsole = $false
    Write-Host "You are likely running this script from Cygwin. In Cygwin use the perl version of tpnc is much better."
}

Write-Verbose "hasConsole = $hasConsole"

$abs_pattern = '^[a-zA-Z]:[\\/]|^[\\/]+|^[\\/]+cygdrive[\\/]+[^\\/]+[\\/]'

if ($outfile) {
    if (!($outfile -match $abs_pattern)) {
        $outfile = "$pwd\$outfile"
    }
    Write-Host "outfile=$outfile"
}

if ($infile) {
    if (!($infile -match $abs_pattern)) {
        $infile = "$pwd\$infile"
    }
    Write-Host "infile=$infile"
}


function SendAndReceive {
    param([Parameter(Mandatory = $true)] $tcpConnection = $null)

    $infile_sent = $false
    $infile_wait_maxloop = 5
    $infile_wait_already = 0

    [System.IO.FileStream]$out_stream = $null
    if ($outfile) {
        try {
            # cannot use OpenWrite, because it cannot handle existing file correctly
            #   $out_stream = [System.IO.File]::OpenWrite($outfile)
            #
            # " 
            #   If you overwrite a longer string (such as "This is a test of the OpenWrite method") with
            #   a shorter string (such as "Second run"), the file will contain a mix of the strings
            #   ("Second runtest of the OpenWrite method").
            # "
            #$out_stream = [System.IO.File]::Open($outfile, FileMode.Create)
            $out_stream = [System.IO.File]::Create($outfile)
        } catch {
            Write-Host $_; exit 1
        }
    }

    $tcpStream = $tcpConnection.GetStream()

    # to transfer binary files, we have to use BinaryReader/BinaryWriter
    # https://stackoverflow.com/questions/10353913/streamreader-vs-binaryreader.
    # StreamReader/StreamWriter only works binary representation of text.
    #   $reader = New-Object System.IO.StreamReader($tcpStream)
    #   $writer = New-Object System.IO.StreamWriter($tcpStream)
    #   $writer.AutoFlush = $true

    $reader = New-Object System.IO.BinaryReader ($tcpStream)
    $writer = New-Object System.IO.BinaryWriter ($tcpStream)

    $buffer = New-Object System.Byte[] 1024
    $encoding = New-Object System.Text.AsciiEncoding

    $recv_total_bytes = 0
    $send_total_bytes = 0

    <#
     TcpClient.Connected isn't really useful

     The Connected property gets the connection state of the Client socket as of the last I/O operation.
     When it returns false, the Client socket was either never connected, or is no longer connected.

     Because the Connected property only reflects the state of the connection as of the most recent
     operation, you should attempt to send or receive a message to determine the current state. After
     the message send fails, this property no longer returns true. Note that this behavior is by design.
     You cannot reliably test the state of the connection because, in the time between the test and a
     send/receive, the connection could have been lost. Your code should assume the socket is connected,
     and gracefully handle failed transmissions
   #>

    while ($tcpConnection.Connected) {
        # empty input queue first
        while ($tcpStream.DataAvailable)
        {
            $size = 0
            $size = $tcpStream.Read($buffer,0,1024)

            if ($size -gt 0) {
                $recv_total_bytes += $size

                Write-Verbose "received $size byte(s). total $recv_total_bytes byte(s)"

                if ($outfile) {
                    $out_stream.Write($buffer,0,$size)
                } else {
                    $text = $encoding.GetString($buffer,0,$size)
                    Write-Host -n $text
                }
            } else {
                # this never worked.
                Write-Host "first time happend. remote closed connection"
                exit 0
            }
        }

        # check whether network connection is still connected
        # https://learn-powershell.net/2015/03/29/checking-for-disconnected-connections-with-tcplistener-using-powershell/
        if (($tcpConnection.Client.Poll(1,[System.Net.Sockets.SelectMode]::SelectRead) -and
                $tcpConnection.Client.Available -eq 0)) {
            Write-Host "remote disconnected"
            break
        }

        if ($infile) {
            if (-not $infile_sent) {
                $in_stream = $null

                if ($infile) {
                    try { $in_stream = [System.IO.File]::OpenRead($infile) }
                    catch { Write-Host $_; exit 1 }
                }

                $in_buffer = New-Object System.Byte[] 1024

                while ($size = $in_stream.Read($in_buffer,0,1024)) {
                    $send_total_bytes += $size
                    Write-Verbose "read $size bytes from file and sending out. total send $send_total_bytes bytes"
                    $writer.Write($in_buffer,0,$size)
                }
                $writer.Flush()

                $infile_sent = $true
            } else {
                # wait a little bit in case the remote wants to send reply
                if ($infile_wait_already -ge $infile_wait_maxloop) {
                    break
                } else {
                    $infile_wait_already++
                }
            }
        } else {
            $read_stdin = $false

            if ($hasConsole) {
                # https://powershell.one/tricks/input-devices/detect-key-press
                if ([Console]::KeyAvailable) {
                    $read_stdin = $true
                }
            } else {
                $read_stdin = $true
            }

            if ($read_stdin) {
                # -prompt doesn't work in Cygwin
                # $line = Read-Host -prompt "hit 'enter' to receive and to send"
                Write-Host -n "hit 'enter' to receive and to send : "
                $line = Read-Host
                $line += "`n"

                # convert text to bytes before sending over
                $bytes = [System.Text.Encoding]::Default.GetBytes($line)
                $size = $bytes.Length

                $send_total_bytes += $size
                Write-Verbose "sending $size byte(s). total $send_total_bytes bytes"

                $writer.Write($bytes) | Out-Null
                $writer.Flush() | Out-Null
            }
        }

        Start-Sleep -Milliseconds 500
    }

    $reader.close()
    $writer.close()

    if ($outfile) {
        # without this, 'dir' will show 0 size on outfile and 'type' command cannot open
        # out file for about 1 minute after command exits.
        # 'type <outfile>' will give "device busy" error.
        $out_stream.close();
    }

    return
}

$listener_port = $l

if ($listener_port) {
    # this is server

    if ($remainingArgs -and $remainingArgs.Count -ne 0) {
        usage ("wrong numnber of args")
    }

    Write-Verbose "listener_port=$listener_port"

    # https://learn-powershell.net/2014/02/22/building-a-tcp-server-using-powershell/

    $listener = New-Object System.Net.Sockets.TcpListener ([system.net.ipaddress]::any,$listener_port)

    if (-not $listener) {
        exit 1
    }

    $listener.Server.SetSocketOption("Socket","ReuseAddress",1)

    try { $listener.start() }
    catch { Write-Host $_; exit 1 }

    Write-Host "listener started at port $listener_port"

    $tcpConnection = $null

    while ($true) {
        if ($listener.Pending()) {
            $tcpConnection = $listener.AcceptTcpClient()
            break;
        }
        Start-Sleep -Milliseconds 1000
    }

    Write-Host "accepted client $($tcpConnection.client.RemoteEndPoint.Address):$($tcpConnection.client.RemoteEndPoint.Port)."

    # we only want to accept one client; therefore, close the listener now.
    $listener.Stop()

    SendAndReceive ($tcpConnection)

    $tcpConnection.close()
} else {
    # this is client

    if (!$remainingArgs -or $remainingArgs.Count -ne 2) {
        usage ("wrong numnber of args")
    }

    $remote_host,$remote_port = $remainingArgs

    Write-Verbose "remote_host=$remote_host"
    Write-Verbose "remote_port=$remote_port"

    $tcpConnection = $null
    try { $tcpConnection = New-Object System.Net.Sockets.TcpClient ($remote_host,$remote_port) }
    catch { Write-Host $_; exit 1 }

    Write-Verbose "connected server $($tcpConnection.client.RemoteEndPoint.Address):$($tcpConnection.client.RemoteEndPoint.Port)."

    SendAndReceive ($tcpConnection)

    $tcpConnection.close()
}

exit 0
