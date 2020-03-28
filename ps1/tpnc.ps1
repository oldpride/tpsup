<#
   To run from cmd.exe, powershell, Cygwin:
   powershell -ExecutionPolicy Bypass -File ./tpnc.ps1 -v localhost 5555

   To see help message
   powershell -ExecutionPolicy Bypass -File ./tpnc.ps1 -?
   tpnc.ps1 [-remote_host] <string> [-remote_port] <string> [-v] [<CommonParameters>]
#>

[CmdletBinding(PositionalBinding=$false)]

param (
    [switch]$v = $false,
    [string]$l = $null,
    #[string]$w = $null,
    [string]$infile  = $null,
    [string]$outfile = $null,
    [Parameter(ValueFromRemainingArguments = $true)]$remainingArgs = $null
)

if ($v) {
   write-host "verbose=$v"
   write-host "listener=$l"
   write-host "wait=$w (seconds)"
   write-host "remaining=$remainingArgs, size=$($remainingArgs.count)"
}

$default_wait = 5

function usage {
  param([string]$message = $null)

  if ($message) {
     write-host $message
  }

  write-host "
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

  #-w seconds          Listener wait these many seconds before quit. default to $default_wait.

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
   [Console]::KeyAvailable | Out-null
}
catch [System.InvalidOperationException] {
   $hasConsole = $false
   Write-Host "You are likely running this script from Cygwin. In Cygwin use the perl version of tpnc is much better."
}

if ($v) { 
   write-host "hasConsole = $hasConsole"
}

function SendAndReceive {
   param ([Parameter(Mandatory = $true)]$tcpConnection = $null)

   $infile_sent = $false
   $infile_wait_maxloop = 5
   $infile_wait_already = 0

   $out_stream = $null
   if ($outfile) {
      try   { 
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

   $reader = New-Object System.IO.BinaryReader($tcpStream)
   $writer = New-Object System.IO.BinaryWriter($tcpStream)

   $buffer = new-object System.Byte[] 1024
   $encoding = new-object System.Text.AsciiEncoding 

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
           $size = $tcpStream.Read($buffer, 0, 1024)

           if ($size -gt 0 ) {
              $recv_total_bytes += $size

              if ($v) { write-host "received $size byte(s). total $recv_total_bytes byte(s)" }

              if ($outfile) {
                 $out_stream.Write($buffer, 0, $size)
              } else {
                 $text = $encoding.GetString($buffer, 0, $size)   
                 write-host -n $text
              }
           } else {
              # this never worked.
              write-host "first time happend. remote closed connection"
              exit 0
           }
       }
   
       # check whether network connection is still connected
       # https://learn-powershell.net/2015/03/29/checking-for-disconnected-connections-with-tcplistener-using-powershell/
       if ( ($tcpConnection.Client.Poll(1,[System.Net.Sockets.SelectMode]::SelectRead) -AND
            $tcpConnection.Client.Available -eq 0)) {
          write-host "remote disconnected"
          break
       }

       if ($infile) {
          if (-Not $infile_sent) {
             $in_stream = $null
             if ($infile) {
                try   { $in_stream = [System.IO.File]::OpenRead($infile) }
                catch { Write-Host $_; exit 1 } 
             }

             $in_buffer = new-object System.Byte[] 1024

             while($size = $in_stream.Read($in_buffer, 0, 1024)) {
                $send_total_bytes += $size
                if ($v) {Write-Host "read $size bytes from file and sending out. total send $send_total_bytes bytes"}
                $writer.Write($in_buffer, 0, $size)
             }
             $writer.flush()

             $infile_sent = $true
          } else {
             # wait a little bit in case the remote wants to send reply
             if ($infile_wait_already -ge $infile_wait_maxloop) {
                break
             } else {
                $infile_wait_already ++
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
             $bytes = [system.Text.Encoding]::Default.GetBytes($line)
             $size = $bytes.Length

             $send_total_bytes += $size
             if ($v) {Write-Host "sending $size byte(s). total $send_total_bytes bytes"}

             $writer.Write($bytes) | Out-Null
             $writer.flush() | Out-Null
          }          
       }
   
       start-sleep -Milliseconds 500
   }

   $reader.Close()
   $writer.Close()

   return
}

$listener_port = $l

if ($listener_port) {
   # this is server

   if ($remainingArgs.count -ne 0) {
      usage("wrong numnber of args")
   }

   if ($v) { write-host "listener_port=$listener_port" }

   # https://learn-powershell.net/2014/02/22/building-a-tcp-server-using-powershell/

   $listener=new-object System.Net.Sockets.TcpListener([system.net.ipaddress]::any, $listener_port)

   if (!$w) {
       $w = $default_wait
   }

   # doesn't work
   #$listener.Server.ReceiveTimeout = $w;
   #$listener.Server.SendTimeout   = $w;

   if (-not $listener) {
      exit 1
   }
   
   try   { $listener.start()     }
   catch { write-host $_; exit 1 }
   
   write-host "listener started at port $listener_port"

   $tcpConnection = $null
   try {
      $tcpConnection = $listener.AcceptTcpClient()
   } catch {
      write-host $_
      exit 1
   }

   write-host "accepted client $($tcpConnection.client.RemoteEndPoint.Address):$($tcpConnection.client.RemoteEndPoint.Port)."

   # we only want to accept one client; therefore, close the listener now.
   $listener.stop()

   SendAndReceive($tcpConnection)
   
   $tcpConnection.Close()
} else {
   # this is client

   if ($remainingArgs.count -ne 2) {
      usage("wrong numnber of args")
   }

   $remote_host,$remote_port = $remainingArgs

   if ($v) {
      write-host "remote_host=$remote_host"
      write-host "remote_port=$remote_port"
   }

   $tcpConnection = $null
   try   {$tcpConnection = New-Object System.Net.Sockets.TcpClient($remote_host, $remote_port)}
   catch { Write-Host $_; exit 1 }

   if ($v) {
      write-host "connected server $($tcpConnection.client.RemoteEndPoint.Address):$($tcpConnection.client.RemoteEndPoint.Port)."
   }

   SendAndReceive($tcpConnection)

   $tcpConnection.Close()
}

exit 0
