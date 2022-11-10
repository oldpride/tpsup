$listener = New-Object System.Net.Sockets.TcpListener ([system.net.ipaddress]::any,4444)
$listener.start()
Write-Host "listener started at port 4444"
while ($true) {
    if ($listener.Pending()) {
        $tcpConnection = $listener.AcceptTcpClient()
        break;
    }
    Start-Sleep -Milliseconds 1000
}
Write-Host "accepted a client"

