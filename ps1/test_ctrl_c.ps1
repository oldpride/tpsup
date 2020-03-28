$listener=new-object System.Net.Sockets.TcpListener([system.net.ipaddress]::any, 4444)
$listener.start()
write-host "listener started at port 4444"
$tcpConnection = $listener.AcceptTcpClient()
write-host "accepted a client"

