<#
   To run from cmd.exe, powershell, Cygwin:
   powershell -ExecutionPolicy Bypass -File ./tpnc.ps1 -v localhost 5555

   To see help message
   powershell -ExecutionPolicy Bypass -File ./tpnc.ps1 -?
   tpnc.ps1 [-remote_host] <string> [-remote_port] <string> [-v] [<CommonParameters>]
#>

<#
what is this for?
[CmdletBinding()]
#>
param (
    [switch]$v = $false,
    #[switch]$l = $false,
    [Parameter(Mandatory=$true)][string]$remote_host,
    [Parameter(Mandatory=$true)][string]$remote_port
)

if ($v) {
   write-host "verbose=$v"
   write-host "listener=$l"
   write-host "remote_host=$remote_host"
   write-host "remote_port=$remote_port"
}

$hasConsole = $true

try { [Console]::KeyAvailable }
catch [System.InvalidOperationException] {$hasConsole = $false}

if ($v) { 
   write-host "hasConsole = $hasConsole"
}

$tcpConnection = New-Object System.Net.Sockets.TcpClient($remote_host, $remote_port)
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
while ($tcpConnection.Connected)
{
    while ($tcpStream.DataAvailable)
    {
        $size = $tcpStream.Read($buffer, 0, 1024)
        $text = $encoding.GetString($buffer, 0, $size)   
        if ($v) {
           write-host "received $size byte(s)"
        }
        write-host -n "$text"
    }

    if ($hasConsole) {
       ## https://powershell.one/tricks/input-devices/detect-key-press
       while ([Console]::KeyAvailable)
       {
           Write-Host -NoNewline "hit 'enter' to receive and to send > "
           $line = Read-Host
           $writer.WriteLine($line) | Out-Null
       }
    } else {
           Write-Host -NoNewline "hit 'enter' to receive and to send > "
           $line = Read-Host
           $writer.WriteLine($line) | Out-Null
    } 

    start-sleep -Milliseconds 500
}

$reader.Close()
$writer.Close()
$tcpConnection.Close()
