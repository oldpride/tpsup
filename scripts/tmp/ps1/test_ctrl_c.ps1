$listener=new-object System.Net.Sockets.TcpListener([system.net.ipaddress]::any, 4444)
$listener.start()
write-host "listener started at port 4444"
while ($true) {
   if ($listener.Pending()) {
      $tcpConnection = $listener.AcceptTcpClient()
      break;
   }
   start-sleep -Milliseconds 1000
}
write-host "accepted a client"

