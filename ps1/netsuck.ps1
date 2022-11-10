[CmdletBinding(PositionalBinding = $false)]
param(
    [string]$outfile = $null,
    [Parameter(ValueFromRemainingArguments = $true)] $remainingArgs = $null
)
Set-StrictMode -Version Latest
function usage {
    param([string]$message = $null)
    if ($message) { Write-Host $message }
    Write-Host "
Usage:
  powershell -ExecutionPolicy Bypass -File ./netsuck.ps1 remote_host remote_port
  As a client, pull in data from a remote server 
  -outfile path       output to a file. default to stdout.
"
    exit 1
}
if (!$remainingArgs -or $remainingArgs.Count -ne 2) { usage ("wrong numnber of args") }
$host1,$port1 = $remainingArgs
$tcpConn = $null
try { $tcpConn = New-Object System.Net.Sockets.TcpClient ($host1,$port1) } catch { Write-Host $_; exit 1 }
$out_stream = $null
if ($outfile) {
    if (!($outfile -match '^[a-zA-Z]:[\\/]|^[\\/]+|^[\\/]+cygdrive[\\/]+[^\\/]+[\\/]')) {
        $outfile = "$pwd\$outfile"
    }
    Write-Host "outfile=$outfile"
    try { $out_stream = [System.IO.File]::Create($outfile) } catch { Write-Host $_; exit 1 }
}
$tcpStream = $tcpConn.GetStream()
$reader = New-Object System.IO.BinaryReader ($tcpStream)
$buffer = New-Object System.Byte[] 1024
$encoding = New-Object System.Text.AsciiEncoding
while ($tcpConn.Connected) {
    while ($tcpStream.DataAvailable) {
        $size = $tcpStream.Read($buffer,0,1024)
        if ($size -gt 0) {
            if ($outfile) { $out_stream.Write($buffer,0,$size) }
            else { Write-Host -n $encoding.GetString($buffer,0,$size) }
        } else { exit 0 }
    }
    if (($tcpConn.Client.Poll(1,[System.Net.Sockets.SelectMode]::SelectRead) -and
            $tcpConn.Client.Available -eq 0)) { break }
    Start-Sleep -Milliseconds 500
}
if ($outfile) { $out_stream.close() }
$reader.close()
$tcpConn.close()
exit 0
