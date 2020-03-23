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

  '-v'      verbose mode.

Examples:

  as a server
     tpnc -l 5555

  as a client
     tpnc localhost 5555

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

   $tcpStream = $tcpConnection.GetStream()
   $reader = New-Object System.IO.StreamReader($tcpStream)
   $writer = New-Object System.IO.StreamWriter($tcpStream)

   $writer.AutoFlush = $true
   
   $buffer = new-object System.Byte[] 1024
   $encoding = new-object System.Text.AsciiEncoding 

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
       while ($tcpStream.DataAvailable)
       {
           $size = 0
           $size = $tcpStream.Read($buffer, 0, 1024)
           #try {$size = $tcpStream.Read($buffer, 0, 1024)}
           #catch [IOException] { write-host "remote closed connection"; exit 0}

           if ($size -gt 0 ) {
              $text = $encoding.GetString($buffer, 0, $size)   
              if ($v) {
                 write-host "received $size byte(s)"
              }
              write-host -n "$text"
           } else {
              write-host "remote closed connection"
              exit 0
           }
       }
   
       if ($hasConsole) {
          ## https://powershell.one/tricks/input-devices/detect-key-press
          while ([Console]::KeyAvailable)
          {
              Write-Host -NoNewline "hit 'enter' to receive and to send > "
              $line = Read-Host
              Write-Host "sending $($line.Length) byte(s)"
              $writer.WriteLine($line) | Out-Null
          }
       } else {
              Write-Host -NoNewline "hit 'enter' to receive and to send > "
              $line = Read-Host
              Write-Host "sending $($line.Length) byte(s)"
              $writer.WriteLine($line) | Out-Null
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
   try   {New-Object System.Net.Sockets.TcpClient($remote_host, $remote_port)}
   catch { Write-Host $_; exit 1 }

   write-host "connected server $($tcpConnection.client.RemoteEndPoint.Address):$($tcpConnection.client.RemoteEndPoint.Port)."

   SendAndReceive($tcpConnection)

   $tcpConnection.Close()
}
