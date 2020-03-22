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
    [Parameter(Mandatory=$true)][string]$remote_host,
    [Parameter(Mandatory=$true)][string]$remote_port
 )

write-host $v
write-host $remote_host
write-host $remote_port

$tcpConnection = New-Object System.Net.Sockets.TcpClient($remote_host, $remote_port)
$tcpStream = $tcpConnection.GetStream()
$reader = New-Object System.IO.StreamReader($tcpStream)
$writer = New-Object System.IO.StreamWriter($tcpStream)
$writer.AutoFlush = $true

$buffer = new-object System.Byte[] 1024
$encoding = new-object System.Text.AsciiEncoding 

while ($tcpConnection.Connected)
{
    while ($tcpStream.DataAvailable)
    {
        $rawresponse = $tcpStream.Read($buffer, 0, 1024)
        $response = $encoding.GetString($buffer, 0, $rawresponse)   
        write-host $response
    }

    if ($tcpConnection.Connected)
    {
        <#
        Write-Host -NoNewline "prompt> "
        #>
        <# https://powershell.one/tricks/input-devices/detect-key-press #>
        $command = Read-Host

        <#
        if ($command -eq "escape")
        {
            break
        }
        #>

        $writer.WriteLine($command) | Out-Null
    }
    start-sleep -Milliseconds 500
}

$reader.Close()
$writer.Close()
$tcpConnection.Close()
