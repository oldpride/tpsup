[CmdletBinding(PositionalBinding=$false)]

param (
    [switch]$v = $false,
    [switch]$reverse = $false,
    [switch]$r       = $false,
    [Parameter(ValueFromRemainingArguments = $true)]$remainingArgs = $null
)

Set-StrictMode -Version Latest
#Set-PsDebug -Trace 1

if ($v) {
   $verbosePreference = "Continue"
}

$version = "7.0"
$version_split = $version -split "[.]"
$expected_peer_protocol = $version_split[0]
Write-Verbose "`$expected_peer_protocol = $expected_peer_protocol"

$reverse = $false
if ($r -or $reverse) {
   $reverse = $true
}
 

function usage {
  param([string]$message = $null)

  if ($message) {
     Write-Host $(get_timestamp) $message
  }

  Write-Host $(get_timestamp) "
Usage:

   tpdist in powershell

   normal mode: server waits to be pulled; client pulls.
     tpdist server local_port
     tpdist client remote_host remote_port remote_path1 remote_path2 ... local_dir

   reversed mode: server waits to take in data; client pushes.
     tpdist server local_port  -reverse remote_port remote_path1 remote_path2 ... local_dir
     tpdist client remote_host remoe_port -reverse

   if remote path is a relative path, it will be relative to remote user's home dir.

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

function get_timestamp {
  return "{0:yyyyMMdd} {0:HH:mm:ss}" -f (Get-Date)
}

$BufferSize = 4*1024*1024
$buffer = new-object System.Byte[] $BufferSize

function send_text {
   param (
      [Parameter(Mandatory = $true)]$writer = $null,
      [Parameter(Mandatory = $true)]$text = $null
   )

   $writer.Write([system.Text.Encoding]::Default.GetBytes($text))
}

function to_pull {
   param (
      [Parameter(Mandatory = $true)]$tcpConnection = $null,
      [Parameter(Mandatory = $true)]$remote_dirs = $null,
      [Parameter(Mandatory = $true)]$local_dirs = $null
   )

   $tcpStream = $tcpConnection.GetStream()

   $reader = New-Object System.IO.BinaryReader($tcpStream)
   $writer = New-Object System.IO.BinaryWriter($tcpStream)

   $encoding = new-object System.Text.AsciiEncoding 

   $remote_dirs_string = $remote_dirs -join "|"

   send_text $writer "<VERSION>$version</VERSION>`n"
   send_text $writer "<PATH>$remote_dirs_string</PATH>`n"
   send_text $writer "<DEEP>0</DEEP>`n"
   send_text $writer "<TREE></TREE>`n"
   send_text $writer "<MAXSIZE>-1</MAXSIZE>`n"
   send_text $writer "<EXCLUDE></EXCLUDE>`n"
   send_text $writer "<MATCH></MATCH>`n"

   $writer.Flush()

   $patterns = @('<NEED_CKSUMS>(.*)</NEED_CKSUMS>')
   
   $captures = @(expect_socket $tcpConnection $tcpStream $reader $writer $patterns @{ExpectTimeout = 300})

   if (!$captures) {
      $reader.Dispose()
      $writer.Dispose()
      $tcpStream.close()
      return
   }

   Write-Verbose "`$captures = $(ConvertTo-Json $captures)"

   $need_cksums_string = $captures[0][0]

   Write-Verbose "received cksum requests, calculating cksums"

   # todo

   $cksums_results_string = ""

   send_text $writer "<CKSUM_RESULTS>$cksums_results_string</CKSUM_RESULTS>"
   $writer.Flush()

   $patterns = @('<DELETES>(.*)</DELETES>',
                 '<MTIMES>(.*)</MTIMES>',
                 '<MODES>(.*)</MODES>',
                 '<SPACE>(\d+)</SPACE>',
                 '<ADDS>(.*)</ADDS>',
                 '<WARNS>(.*)</WARNS>')


   $captures = @(expect_socket $tcpConnection $tcpStream $reader $writer $patterns @{ExpectTimeout = 3})

   if (!$captures) {
      $reader.Dispose()
      $writer.Dispose()
      $tcpStream.Close()
      return
   }

   $deletes_string = $captures[0][0];
   $mtimes_string  = $captures[1][0];
   $modes_string   = $captures[2][0];
   $RequiredSpace  = $captures[3][0];
   $adds_string    = $captures[4][0];
   $warns_string   = $captures[5][0];

   $local_dir_abs = get_abs_path $local_dir
   if ( -not (Test-Path -Path $local_dir_abs)) {
      Write-Host $(get_timestamp) "creating directory $local_dir_abs"
      try { New-Item -ItemType "directory" -Path $local_dir_abs -Force }
      catch { Write-Error $_; exit 1}     
   }
   Write-Host $(get_timestamp) "cd $local_dir_abs"

   #Set-Location -Path $local_dir_abs
   cd $local_dir_abs

   send_text $writer "please send data`n"
   $writer.Flush()

   $temp_file = [System.IO.Path]::GetTempFileName()
   $tmp_tar_file = [System.IO.Path]::ChangeExtension($temp_file, ".tar")
   Move-Item $temp_file $tmp_tar_file   

   Write-Host $(get_timestamp) "waiting for data from remote, will write to $tmp_tar_file"

   # create an FileStream for output
   $out_stream = $null
   try   { $out_stream = [System.IO.File]::Create($tmp_tar_file)}
   catch { Write-Host $(get_timestamp) $_; exit 1}

   $total_size = 0

   while ($tcpConnection.Connected) {     
      while ($tcpStream.DataAvailable) {
         $size = $tcpStream.Read($buffer, 0, $BufferSize)

         if ($size -gt 0 ) {
            $recv_total_bytes += $size
            write-verbose "received $size byte(s). total $recv_total_bytes byte(s)"  
            $out_stream.Write($buffer, 0, $size)            
         } else {
              # this never worked.
              Write-Host $(get_timestamp) "first time happend. remote closed connection"
              exit 0
         }
      }

      if ( ($tcpConnection.Client.Poll(1,[System.Net.Sockets.SelectMode]::SelectRead) -AND
            $tcpConnection.Client.Available -eq 0)) {
          Write-Host $(get_timestamp) "remote disconnected"
          break
      }

      #start-sleep -Milliseconds 1000
      sleep 1
   }

   $out_stream.flush()
   $out_stream.dispose()

   dir $tmp_tar_file

   # 1. tar -xvf $tmp_tar_file send veriticalut to outp stdout. therefore, use 2 commands instead
   # 2.need to wait external command to finish before remove the $tmp_tar_file, eg, use |Out_Host
   #    https://stackoverflow.com/questions/1741490/how-to-tell-powershell-to-wait-for-each-command-to-end-before-starting-the-next
   tar -tf $tmp_tar_file |Out-Host
   tar -xf $tmp_tar_file |Out-Host

   Remove-Item $tmp_tar_file
}

function to_be_pulled {
   param (
      [Parameter(Mandatory = $true)]$tcpConnection = $null,
      $opt = $null
   )

   Write-Host $(get_timestamp), "waiting information from remote ...`n";

   $patterns = @(       
      '<PATH>(.+)</PATH>',
      '<TREE>(.*)</TREE>',
      '<MAXSIZE>([-]?\d+)</MAXSIZE>',
      '<VERSION>(.+)</VERSION>',
      '<EXCLUDE>(.*)</EXCLUDE>',
      '<MATCH>(.*)</MATCH>',
      '<DEEP>(.)</DEEP>'
   )

   $captures = @(expect_socket $tcpConnection $tcpStream $reader $writer $patterns @{ExpectTimeout = 3})

   if (!$captures) {
      $reader.Dispose()
      $writer.Dispose()
      $tcpStream.Close()
      return
   }

   $local_paths_string  = $captures[0][0]
   $remote_tree_block   = $captures[1][0]
   $maxsize             = $captures[2][0]
   $remote_version      = $captures[3][0]
   $exclude_string      = $captures[4][0]
   $match_string        = $captures[5][0]
   $deep_check          = $captures[6][0]

   $remote_version_split = $remote_version -split "[.]";
   $peer_protocol = $remote_version_split[0]

   if ($peer_protocol -ne $expected_peer_protocol) {
      Write-Host $(get_timestamp), "remote used wrong protocol $peer_protocol, we are expecting protocol $expected_peer_protocol. we closed the connection.\n";
      $writer.Write("wrong protocol $peer_protocol, we are expecting protocol $expected_peer_protocol")
      $writer.Flush()
      return;
   }

   $remote_tree = @{}

   if ($remote_tree_block -ne "") {
      $lines = $remote_tree_block -split "`n"

      foreach ($l in $lines) {
         if (! ($l -match "^key="))  {
            next
         }

         $pairs = $l -split "[|]"
         $branch = @{}
         foreach ($pair in $pairs) {
            $k,$v = $pair -split "=", 2
            $branch[$k] = $v
         }

         $remote_tree[$branch["key"]] = $branch
      }
   }


}

function build_dir_tree {
   param (
      [Parameter(Mandatory = $true)][string[]]$localpaths = $null,
      [hashtable]$opt = $null
   )

   $deny_patterns = $null
   $allow_patterns = $null

   if ($opt["denyfile"]) {
      sleep 1;
      
   }
}

function expect_socket {
   param (
      [Parameter(Mandatory = $true)]$tcpConnection = $null,
      [Parameter(Mandatory = $true)]$tcpStream = $null,
      [Parameter(Mandatory = $true)][System.IO.BinaryReader]$reader = $null,
      [Parameter(Mandatory = $true)][System.IO.BinaryWriter]$writer = $null,
      [Parameter(Mandatory = $true)][string []]$patterns = $null,
      $opt = $null
   )

   $data_str = ""
   $num_patterns = $patterns.count
   $matched = New-Object boolean[] $num_patterns
   $captures = New-Object object[] $num_patterns 
   $other = @{}
   $total_wait = 0
   
   while ($tcpConnection.Connected) {
       while ($tcpStream.DataAvailable) {
           $size = $tcpStream.Read($buffer, 0, $BufferSize)

           if ($size -gt 0 ) {
              $recv_total_bytes += $size
              write-verbose "received $size byte(s). total $recv_total_bytes byte(s)"              
              $text = $encoding.GetString($buffer, 0, $size)   
              $data_str += $text              
              write-verbose "data_str=$data_str"

              $all_matched = $true
                            
              for ($i = 0; $i -lt $num_patterns; $i++){ 
                 if ($matched[$i]) {
                    continue;
                 }
                 # Set-PsDebug -Trace 2
                 # multiline regex use "(?s)"
                 if ($data_str -match "(?s)$($patterns[$i])") {
                    $matched[$i] = $true
                    $captures[$i] = @($Matches[1], $Matches[2], $Matches[3])    # Matches[0] is the whole string
                 } else {
                    $all_matched = $false
                 }  
                 # Set-PsDebug -Trace 0                 
              }
                 
              if ($all_matched) {
                 Write-Verbose "`$captures = $(ConvertTo-Json $captures)"
                 return $captures
              }                       
           } else {
              # this never worked.
              Write-Host $(get_timestamp) "first time happend. remote closed connection"
              exit 1
           }
       }
   
       # check whether network connection is still connected
       # https://learn-powershell.net/2015/03/29/checking-for-disconnected-connections-with-tcplistener-using-powershell/
       if ( ($tcpConnection.Client.Poll(1,[System.Net.Sockets.SelectMode]::SelectRead) -AND
            $tcpConnection.Client.Available -eq 0)) {
          $last_words = ""
          if ($data_str -ne "") {
             $tail_size = 100
             if ($data_str.Length -le $tail_size ) {
                $last_words = $data_str
             } else {
                $last_words = $data_str.Substring($data_str.Length - $tail_size + 1)
             }
          }
          Write-Error "remote side closed connection. Last words: $last_words"
          return $null
       }

       if ($opt["ExpectTimeout"]) {
          if ($total_wait -gt $opt['ExpectTimeout']) {
             $message = "timed out after $($opt['ExpectTimeout']) seconds. very likely wrong protocol. expecting $expected_peer_protocol.*"
             Write-Error $message
             $writer.Write([system.Text.Encoding]::Default.GetBytes($message))
             $writer.Flush();
             sleep 2; # give a little time so that remote can process this messsage
             
             for (my $i=0; $i -lt $num_patterns; $i++) {
                if ($matched[$i]) {
                   Write-Host "   pattern=$($patterns[$i])  matched"
                } else {
                   Write-Host "   pattern=$($patterns[$i])  didn't matched"
                }
             }
             return $null
          }         
       }
       sleep 1
       $total_wait ++
   }
}

# https://stackoverflow.com/questions/3038337/powershell-resolve-path-that-might-not-exist
function get_abs_path {
   param (
      [Parameter(Mandatory = $true)]$path = $null,
      $opt = $null
   )

   $abs_path = Resolve-Path $path -ErrorAction SilentlyContinue `
                                  -ErrorVariable myerror
    if (-not($abs_path)) {
        $abs_path = $myerror[0].TargetObject
    }

    return $abs_path
}

<#
function dummy {
       if ($infile) {
          if (-Not $infile_sent) {
             $in_stream = $null
             if ($infile) {
                try   { $in_stream = [System.IO.File]::OpenRead($infile) }
                catch { Write-Host $(get_timestamp) $_; exit 1 } 
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
             Write-Host $(get_timestamp) -n "hit 'enter' to receive and to send : "
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

$old_pwd = $pwd

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
   catch { Write-Host $(get_timestamp) $_; exit 1 }
   
   Write-Host $(get_timestamp) "listener started at port $listener_port"

   $tcpConnection = $null

   while ($true) { 
      if ($listener.Pending()) {
         $tcpConnection = $listener.AcceptTcpClient()
         break;
      }
      start-sleep -Milliseconds 1000
   }

   Write-Host $(get_timestamp) "accepted client $($tcpConnection.client.RemoteEndPoint.Address):$($tcpConnection.client.RemoteEndPoint.Port)."

   # we only want to accept one client; therefore, close the listener now.
   $listener.stop()

   SendAndReceive($tcpConnection)
   
   $tcpConnection.Close()
} else {
   # this is client

   if (!$remainingArgs) {
      usage("wrong numnber of args")
   }

   if ($reverse) {
      if ($remainingArgs.count -ne 2) {
         usage("wrong numnber of args")
      }
   } else {
      if ($remainingArgs.count -lt 5) {
         usage("wrong numnber of args")
      }
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
   catch { Write-Host $(get_timestamp) $_; exit 1 }

   write-verbose "connected server $($tcpConnection.client.RemoteEndPoint.Address):$($tcpConnection.client.RemoteEndPoint.Port)"

   if ($reverse) {
      to_be_pulled $tcpConnection
   } else {
      to_pull $tcpConnection $remote_dirs $local_dir
   }

   $tcpConnection.Close()

   Write-Host $(get_timestamp) "going back to old pwd: cd $old_pwd"

   #Set-Location -Path $old_pwd
   cd $old_pwd
}

exit 0
