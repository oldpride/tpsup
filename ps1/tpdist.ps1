[CmdletBinding(PositionalBinding=$false)]

param (
    [switch]$v = $false,
    [Parameter(ValueFromRemainingArguments = $true)]$remainingArgs = $null
)

Set-StrictMode -Version Latest
#Set-PsDebug -Trace 1

$version = "7.0"

if ($v) {
   $verbosePreference = "Continue"
}   
 

function usage {
  param([string]$message = $null)

  if ($message) {
     write-host $message
  }

  write-host "
Usage:

  tpdist in powershell

  as a server
     tpdist server port

  as a client
     tpdist client server_host server_port source_path target_dir

  -v                  verbose mode.

Examples:

  as a server
     tpdist.ps1 server 5555

  as a client
     tpdist.ps1 client localhost 5555 /cygdrive/c/Users/william/github/tpsup/ps1 tmp 

     tpdist.ps1 client localhost 5555 'C:/users/william/github/tpsup/ps1' 'C:/users/william/github/tpsup/kdb' /tmp

"

   exit 1
}

$BufferSize = 4*1024*1024
$ReadBuffer = new-object System.Byte[] $BufferSize

function SendText {
   param (
      [Parameter(Mandatory = $true)]$writer = $null,
      [Parameter(Mandatory = $true)]$text = $null
   )

   $writer.Write([system.Text.Encoding]::Default.GetBytes($text))
}

function Pull {
   param (
      [Parameter(Mandatory = $true)]$tcpConnection = $null,
      [Parameter(Mandatory = $true)]$remote_dirs = $null,
      [Parameter(Mandatory = $true)]$local_dirs = $null
   )

   $tcpStream = $tcpConnection.GetStream()

   $reader = New-Object System.IO.BinaryReader($tcpStream)
   $writer = New-Object System.IO.BinaryWriter($tcpStream)

   $encoding = new-object System.Text.AsciiEncoding 

   $recv_total_bytes = 0
   $send_total_bytes = 0

   $remote_dirs_string = $remote_dirs -join "|"

   SendText $writer "<VERSION>$version</VERSION>`n"
   SendText $writer "<PATH>$remote_dirs_string</PATH>`n"
   SendText $writer "<DEEP>0</DEEP>`n"
   SendText $writer "<TREE></TREE>`n"
   SendText $writer "<MAXSIZE>-1</MAXSIZE>`n"
   SendText $writer "<EXCLUDE></EXCLUDE>`n"
   SendText $writer "<MATCH></MATCH>`n"

   $writer.Flush()

   $patterns = @('<NEED_CKSUMS>(.*)</NEED_CKSUMS>')
   
   $matched, $captures, $other = ExpectSocket $tcpConnection $tcpStream $reader $patterns @{ExpectTimeout = 3}

   $need_cksums_string = $null
   if ($other["status"] -eq 'done') {
      $need_cksums_string = $captures[0][0]
      Write-Verbose "need_cksums_string=$need_cksums_string"
   } else {
      Write-Error $other["status"]
      exit 1
   }

   Write-Verbose "received cksum requests, calculating cksums"

   # todo

   $cksums_results_string = ""

   SendText $writer "<CKSUM_RESULTS>$cksums_results_string</CKSUM_RESULTS>"
   $writer.Flush()

   $patterns = @('<DELETES>(.*)</DELETES>',
                 '<MTIMES>(.*)</MTIMES>',
                 '<MODES>(.*)</MODES>',
                 '<SPACE>(\d+)</SPACE>',
                 '<ADDS>(.*)</ADDS>',
                 '<WARNS>(.*)</WARNS>')


   $matched, $captures, $other = ExpectSocket $tcpConnection $tcpStream $reader $patterns @{ExpectTimeout = 3}

   $deletes_string = ""
   $mtimes_string  = ""
   $modes_string   = ""
   $adds_string    = ""
   $warns_string   = ""
   $RequiredSpace  = -1

   if ($other["status"] -eq 'done') {
      $deletes_string = $captures[0][0];
      $mtimes_string  = $captures[1][0];
      $modes_string   = $captures[2][0];
      $RequiredSpace  = $captures[3][0];
      $adds_string    = $captures[4][0];
      $warns_string   = $captures[5][0];
   } else {
      for ($i = 0; $i -lt $matched.count; $i++) { 
         if ($matched[$i]) {
            Write-Host "$($patterns[$i]) matched"
         } else {
            Write-Host "$($patterns[$i]) didn't match"
         } 
      }
      Write-Error $other["status"]
      exit 1
   }

   $local_dir_abs = Resolve-Path $local_dir
   Set-Location -Path $local_dir_abs

   WriteText $writer "please send data`n"
   $writer.Flush()

   Write-Host "waiting for data from remote\n"

   $total_size = 0

   $temp_file = [System.IO.Path]::GetTempFileName()
   $tar_file = [System.IO.Path]::ChangeExtension($temp_file, ".tar")
   Move-Item $temp_file $tar_file

   

   $out_stream = $null
   try   { $out_stream = [System.IO.File]::Create($tar_file)}
   catch { Write-Host $_; exit 1}

   while ($tcpConnection.Connected) {     
      while ($tcpStream.DataAvailable) {
         $size = $tcpStream.Read($ReadBuffer, 0, $BufferSize)

         if ($size -gt 0 ) {
            $recv_total_bytes += $size
            write-verbose "received $size byte(s). total $recv_total_bytes byte(s)"  
            $out_stream.Write($buffer, 0, $size)            
         } else {
              # this never worked.
              write-host "first time happend. remote closed connection"
              exit 0
         }
      }

      if ( ($tcpConnection.Client.Poll(1,[System.Net.Sockets.SelectMode]::SelectRead) -AND
            $tcpConnection.Client.Available -eq 0)) {
          write-host "remote disconnected"
          break
      }

      start-sleep -Milliseconds 1000
   }

   Write-Verbose $tar_file
   # Remove-Item $receive_tar

}

function ExpectSocket {
   param (
      [Parameter(Mandatory = $true)]$tcpConnection = $null,
      [Parameter(Mandatory = $true)]$tcpStream = $null,
      [Parameter(Mandatory = $true)]$reader = $null,
      [Parameter(Mandatory = $true)]$patterns = $null,
      $opt = $null
   )

   $data_str = ""
   $num_patterns = $patterns.count
   $matched = New-Object boolean[] $num_patterns
   $captures = New-Object object[] $num_patterns 
   $other = @{}
   $total_wait = 0

   Write-Verbose "ExpectSocket"
   
   while ($tcpConnection.Connected) {
       # empty input queue first
       while ($tcpStream.DataAvailable)
       {
           $size = 0
           $size = $tcpStream.Read($ReadBuffer, 0, $BufferSize)

           if ($size -gt 0 ) {
              $recv_total_bytes += $size
              write-verbose "received $size byte(s). total $recv_total_bytes byte(s)"              
              $text = $encoding.GetString($ReadBuffer, 0, $size)   
              $data_str += $text
              
              write-verbose "data_str=$data_str"

              $all_matched = $true
              
              for ($i = 0; $i -lt $num_patterns; $i++){ 
                 if ($matched[$i]) {
                    next;
                 }
                 # Set-PsDebug -Trace 2
                 # https://docs.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_regular_expressions?view=powershell-7
                 Write-Verbose "pattern=$patterns[$i]"
                 if ($data_str -match $patterns[$i]) {
                 #if ($data_str -match '<CKSUM_RESULTS>(.*)</CKSUM_RESULTS>') {
                    $matched[$i] = $true
                    $captures[$i] = ($Matches[1], $Matches[2], $Matches[3])    # Matches[0] is the whole string
                 } else {
                    $all_matched = $false
                 }  
                 # Set-PsDebug -Trace 0                 
              }
                 
              if ($all_matched) {
                 $other["status"] = "done"
                 return ($matched, $captures, $other)
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

       if ($opt["ExpectTimeout"]) {
          if ($total_wait -gt $opt['ExpectTimeout']) {
             Write-Verbose "ExpectSocket timed out after $($opt['ExpectTimeout']) seconds\n"
             $other["status"] = "timed out"
             return ($matched, $captures, $other)
          }
          
       }
       start-sleep -Milliseconds 1000
       $total_wait ++
   }
}

<#
function dummy {
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
                Write-Verbose "read $size bytes from file and sending out. total send $send_total_bytes bytes"
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
             Write-Verbose "sending $size byte(s). total $send_total_bytes bytes"

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
#>

if (!$remainingArgs) {
   usage("wrong number of args")
}

write-verbose "verbose=$v"
write-verbose "remainingArgs=$remainingArgs, size=$($remainingArgs.count)"

$role = $remainingArgs[0]

if ($role.ToLower() -ne 'server' -AND $role.ToLower() -ne 'client') {
   usage("Role must be either 'server' or 'client'")
}

if ($role.ToLower() -eq 'server') {
   # this is server

   if (!$remainingArgs -OR $remainingArgs.count -ne 2) {
      usage("wrong numnber of args")
   }

   $listener_port = $remainingArgs[1]

   write-verbose "listener_port=$listener_port"

   $listener=new-object System.Net.Sockets.TcpListener([system.net.ipaddress]::any, $listener_port)

   if (-not $listener) {
      exit 1
   }
   
   try   { $listener.start()     }
   catch { write-host $_; exit 1 }
   
   write-host "listener started at port $listener_port"

   $tcpConnection = $null

   while ($true) { 
      if ($listener.Pending()) {
         $tcpConnection = $listener.AcceptTcpClient()
         break;
      }
      start-sleep -Milliseconds 1000
   }

   write-host "accepted client $($tcpConnection.client.RemoteEndPoint.Address):$($tcpConnection.client.RemoteEndPoint.Port)."

   # we only want to accept one client; therefore, close the listener now.
   $listener.stop()

   SendAndReceive($tcpConnection)
   
   $tcpConnection.Close()
} else {
   # this is client

   if (!$remainingArgs -OR $remainingArgs.count -lt 5) {
      usage("wrong numnber of args")
   }

   $remote_host,$remote_port = $remainingArgs[1..2]
   $local_dir = $remainingArgs[-1]
   $remote_dirs = $remainingArgs[3..($remainingArgs.count-2)]


   write-verbose "remote_host=$remote_host"
   write-verbose "remote_port=$remote_port"
   write-verbose "remote_dirs=$remote_dirs, size=$($remote_dirs.count)"
   write-verbose "local_dir=$local_dir"

   $tcpConnection = $null
   try   {$tcpConnection = New-Object System.Net.Sockets.TcpClient($remote_host, $remote_port)}
   catch { Write-Host $_; exit 1 }

   write-verbose "connected server $($tcpConnection.client.RemoteEndPoint.Address):$($tcpConnection.client.RemoteEndPoint.Port)"

   Pull $tcpConnection $remote_dirs $local_dir

   $tcpConnection.Close()
}

exit 0
