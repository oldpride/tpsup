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
    [string]$infile  = $null,
    [string]$outfile = $null,
    [Parameter(ValueFromRemainingArguments = $true)]$remainingArgs = $null
)

if ($v) {
   write-host "verbose=$v"
   write-host "listener=$l"
   write-host "remaining=$remainingArgs, size=$($remainingArgs.count)"
}

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

Examples:

  as a server
     powershell -ExecutionPolicy Bypass -File ./tpnc.ps1 -l 5555

  as a client
     powershell -ExecutionPolicy Bypass -File ./tpnc.ps1 localhost 5555

  to transfer binary file
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
try { [Console]::KeyAvailable | Out-null}
catch [System.InvalidOperationException] {$hasConsole = $false}

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
      try   { $out_stream = [System.IO.File]::OpenWrite($outfile) }
      catch { Write-Host $_; exit 1 } 
   }


   $tcpStream = $tcpConnection.GetStream()

   # to transfer binary files, we have to use BinaryReader/BinaryWriter
   # https://stackoverflow.com/questions/10353913/streamreader-vs-binaryreader.
   # StreamReader/StreamWriter only works binary representation of text.
   #   $reader = New-Object System.IO.StreamReader($tcpStream)
   #   $writer = New-Object System.IO.StreamWriter($tcpStream)
   $reader = New-Object System.IO.BinaryReader($tcpStream)
   $writer = New-Object System.IO.BinaryWriter($tcpStream)

   $writer.AutoFlush = $true
   
   $buffer = new-object System.Byte[] 1024
   $encoding = new-object System.Text.AsciiEncoding 

   $recv_total_bytes = 0

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
           #try {$size = $tcpStream.Read($buffer, 0, 1024)}
           #catch [IOException] { write-host "remote closed connection"; exit 0}

           if ($size -gt 0 ) {
              $recv_total_bytes += $size

              if ($v) {
                 write-host "received $size byte(s). total $recv_total_bytes byte(s)"
              }

              if ($outfile) {
                 $out_stream.Write($buffer, 0, $size)
              } else {
                 $text = $encoding.GetString($buffer, 0, $size)   
                 write-host -n "$text"
              }
           } else {
              # this never worked.
              write-host "remote closed connection"
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
             # https://stackoverflow.com/questions/24708859/output-binary-data-on-powershell-pipeline/24745250#24745250
             # https://stackoverflow.com/questions/4533570/in-powershell-how-do-i-split-a-large-binary-file
             #$indata = $null
             #try { $indata = (Get-Content $infile -encoding byte) }
             #catch {write-host $_; exit 1}
             #$size = $indata.length
             #$writer.Write($indata, 0, $indata.length)

             $in_stream = $null
             if ($infile) {
                try   { $in_stream = [System.IO.File]::OpenRead($infile) }
                catch { Write-Host $_; exit 1 } 
             }

             $in_buffer = new-object System.Byte[] 1024
             $total_bytes = 0

             while($in_size = $in_stream.Read($in_buffer, 0, 1024)) {
                $total_bytes += $in_size 
                Write-Host "read $in_size bytes from file and sending out. total $total_bytes bytes"
                $writer.Write($in_buffer, 0, $in_size)
                #$writer.flush()
                #start-sleep -Milliseconds 500
             }

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
          if ($hasConsole) {
             ## https://powershell.one/tricks/input-devices/detect-key-press
             while ([Console]::KeyAvailable)
             {
                 Write-Host -NoNewline "hit 'enter' to receive and to send > "
                 $line = Read-Host
                 Write-Host "sending $($line.Length) byte(s) + line ends"
                 $writer.WriteLine($line) | Out-Null
             }
          } else {
                 Write-Host -NoNewline "hit 'enter' to receive and to send > "
                 $line = Read-Host
                 Write-Host "sending $($line.Length) byte(s) + line ends"
                 $writer.WriteLine($line) | Out-Null
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

   if ($v) {
      write-host "listener_port=$listener_port"
   }

   # https://learn-powershell.net/2014/02/22/building-a-tcp-server-using-powershell/

   $listener=new-object System.Net.Sockets.TcpListener([system.net.ipaddress]::any, $listener_port)

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

   write-host "connected server $($tcpConnection.client.RemoteEndPoint.Address):$($tcpConnection.client.RemoteEndPoint.Port)."

   SendAndReceive($tcpConnection)

   $tcpConnection.Close()
}
