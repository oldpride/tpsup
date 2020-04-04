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
      [Parameter(Mandatory = $true)][string[]]$paths = $null,
      [hashtable][hashtable]$opt = $null
   )

   $old_cwd = $pwd
   
   $tree = @{}
   $other = @{}

   $AllowDenyPatterns = $opt["AllowDenyPatterns"]

   foreach ($path in $paths) {
      if ($opt["RelativeBase"] -and ! ($path -match "^/")) {
         Write-Verbose "cd $($opt["RelativeBase"])"

         # in powershell, try{}catch{} only catches terminating errors. 
         # 'cd' will not cause terminating error. therefore, we cannot use
         # try/catch. instead, we use $? which is $true/$false, not 0/1
         cd $opt["RelativeBase"]
         if (!$?) {
            Write-Host "$(get_timestampe) cd $($opt["RelativeBase"]) failed. $path is skipped"
            continue
         }        
      }

      $globs = @(Resolve-Path -Path $path|Select -ExpandProperty "Path")

      if (!$?) {
         $message = "dir $path failed. skipped $path"
         Write-Host "$(get_timestamp) $message"
         set_hash_of_arrays $other "error" $message
         continue
      }

      Write-Host "$(get_timestamp) resolved globs if any: $path => $(ConvertTo-Json $globs)"

      foreach ($p in $globs) {
         $abs_path = $null
         if ( ($p -match "[a-zA-Z]:^[/\]") -or ($p -match "^[/\]") ) {
            # examples: C://users, C:\\users, //netappsrv/data, \\netappsrv\data

            # this is abs path, still simplify it: a/../b -> b
            $abs_path = get_abs_path($p)
         } else {
            if ($opt["RelativeBase"]) {
               $abs_path = get_abs_path("$($opt["RelativeBase"])\$p")
            } else {
               $abs_path = get_abs_path("$cwd\$p")
            }
         }

         if (!$abs_path) {
            $message = "cannot find abs_path for $p. skipped"
            write-host "$(get_time_stamp) $message"
            set_hash_of_arrays $other "error" $message
            continue
         }

         if (! (Test-Path $abs_path) -and ! (Get-ItemProperty william).LinkType ) {
            # https://stackoverflow.com/questions/817794/find-out-whether-a-file-is-a-symbolic-link-in-powershell
            # to-do, not sure windows tar can handle broken symbolic links
            $message = "cannot find $abs_path for $p. skipped"
            Write-Host "$(get_timestamp) $message"
            set_hash_of_arrays $other "error" $message
            continue;
         }

         if ($abs_path -match '^[/\]+$') {
            Write-Error "cannot handle $abs_path for $p"
            exit 1
         }

         # $back is the starting point to compare, a relative path
         # $front is the parent path (absolute path)
         # example:
         #    $0 client host port /a/b/*.csv /c/d/e f/g
         # $back will be *.csv and e.
         # when comparing *.csv, server needs to 'cd /a/b'. client needs to 'cd /f/g'.
         # when comparing e, server needs to 'cd /c/d'. client needs to 'cd /f/g'.

         $front = $null
         $back  = $null

         if ($abs_path -match '^(.*[\/])(.+)') {
            $front,$back = $Matches[1],$Matches[2]
         } else {
            Write-Error "unexpected path $abs_path"
            exit 1
         }

         if (!(is_allowed $abs_path $AllowDenyPatterns $opt)) {
            set_nested_hash $other @("skipped_back", $back) "denied"
            continue
         }

         Write-Host "cd '$front'"
         cd $front
         if (!$?) {
            exit 1
         }

         # foreach ($f in @(Get-ChildItem -Recurse tmp)) { ConvertTo-Json $f}
         # foreach ($f in @(Get-ChildItem -Recurse tmp\ps1\List-Exe.ps1)) { ConvertTo-Json $f}
         # foreach ($f in @(Get-ChildItem -Recurse -Directory tmp)) { ConvertTo-Json $f}
         # foreach ($f in @(Get-ChildItem -Recurse tmp)) { write-host "$($f.DirectoryName)\$($f.Name) $($f.LastWriteTime)"}
         # foreach ($f in @(Get-ChildItem -Recurse tmp)) { write-host "$($f.FullName) $($f.Mode) $($f.length) $($f.LastWriteTime) PSIsContainer=$($f.PSIsContainer) LinkType=$($f.LinkType)"}
         # Get-ChildItem -Recurse tmp | wheres FullName match 'tpnc'

         # how to read Mode
         # https://stackoverflow.com/questions/4939802/what-are-the-possible-mode-values-returned-by-powershells-get-childitem-cmdle
         # d - Directory
         # a - Archive
         # r - Read-only
         # h - Hidden
         # s - System
         # l - Reparse point, symlink, etc.

         $file_count = 0
         :FILES foreach ($item in @(Get-ChildItem -Recurse $back)) {
            $file_count ++
            if ($file_count % 10000 -eq 0) {
               Write-Host "$(get_timestamp) checked $file_count files"
            }

            $f = item.FullName

            if ($opt["matches"]) {
               $matched = $false
               # $hash_of_array = @{ 'a'= @(1,2,3)}
               # ConvertTo-Json $hash_of_array['a']
               foreach ($m in $opt["matches"]) {
                  if ($f -match $m) {
                     $matched = $true
                     last
                  }
               }
               if (!$matched) {
                  continue
               }
            }
         }

         if ($opt["excludes"]) {
            foreach ($m in $opt["excludes"]) {
               if ($f -match $m) {
                  continue FILES
               }
            }
         }         

         if (!(is_allowed($f, $AllowDenyPatterns)) ) {
            set_nested_hash $tree @($f, "skip") "not allowed"
            continue
         }

         if (!(Test-Path -LiteralPath $f -ErrorAction SilentlyContinue)) {
            set_nested_hash $tree @($f, 'skip') "no access"
            contiue
         }
          
         if (get_nested_hash $tree @($f, 'back')) {
            set_nested_hash $tree @($f, 'skip') "duplicate target path: skip $front/$f"
            continue
         } else {
            set_nested_hash $tree @($f, 'back') $back
         }

         $mtime   = $item.lastWriteTime
         $winmode = $item.Mode
         $size    = $item.Length

         $type = "file"
         if ($item.PSIsContainer) {
            $type = "dir"
         } elsif ($item.LinkType) {
            $type = "link"
         }






      }

   }
}

function tar_file_list {
  param (
      [Parameter(Mandatory = $true)][hashtable]$front = $null,
      [Parameter(Mandatory = $true)][string]$tar = $null,
      [Parameter(Mandatory = $true)][string []]$files = $null,
      [Parameter(Mandatory = $true)][boolean]$create = $null,
      [hashtable]$opt = $null
   )

   # C:\users\william\tmp\ps1\List-Exe.ps1
   # C:\users\william\tmp\ps1\netsuck.ps1
   # C:\users\william\tmp\ps1\print_key.ps1
   # C:\users\william\tmp\ps1\tpnc.ps1
   # cd C:\users\william\
   # echo "tmp\ps1\List-Exe.ps1" > test_list.txt
   # echo "tmp\ps1\netsuck.ps1" >> test_list.txt
   # type test_list.txt
   # tar -cvf test.tar -T test_list.txt # this doesn't work as -t and -T is ambiguous in windows
   # -v somehow causing error, therefore we use -cf instead of -cvf below
   # tar -cf test.tar "tmp\ps1\List-Exe.ps1" "tmp\ps1\netsuck.ps1"
   # tar -tvf test.tar
   # tar -uf test.tar "tmp\ps1\print_key.ps1" "tmp\ps1\tpnc.ps1"
   # tar -tvf test.tar
   # rm test.tar

   # wrap each file name with quotes to take the spaces in filenames
   $file_string = @(foreach ($f in $files) {"'$f'"}) -join " "
   $substring = $file_string
   if ($file_string.Length -gt 30) {
      $substring = "$($file_string.Substring(0,50)) ..."
   }

   Write-Host "$(get_timestamp) cd $front; tar -cf $tar $substring"

   $saved_tar_pwd = $pwd
   cd $front

   $command = $null
   if ($create) {
      # -v switch triggers an error, therefore, we don't use it
      # PS C:\users\william> tar -cvf test.tar "tmp\ps1\List-Exe.ps1"|Out-Null
      # tar : a tmp/ps1/List-Exe.ps1
      # At line:1 char:1
      # + tar -cvf test.tar "tmp\ps1\List-Exe.ps1"|Out-Null
      # + ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
      #    + CategoryInfo          : NotSpecified: (a tmp/ps1/List-Exe.ps1:String) [], RemoteException
      #    + FullyQualifiedErrorId : NativeCommandError

      $command = "tar -cf $tar $file_string"
   } else {
      $command = "tar -uf $tar $file_string"
   }
   Invoke-Expression $command | Out-Host
   
   cd $saved_tar_pwd
}

function set_hash_of_arrays {
  param (
      [Parameter(Mandatory = $true)][hashtable]$hash = $null,
      [Parameter(Mandatory = $true)][string]$key = $null,
      [Parameter(Mandatory = $true)]$value = $null,
      $opt = $null
   )

   # we need a self-initialized hash of arrays. therefore, we implement this function
   # https://powershell.org/forums/topic/working-with-hash-of-arrays/

   if ($hash[$key]) {
      $hash[$key] += $value
   } else {
      $hash[$key] = @($value)
   }
}

function set_hash_of_arrays_test {
   $test_hash = @{}
   set_hash_of_arrays $test_hash "test_key" "test_value_1"
   set_hash_of_arrays $test_hash "test_key" "test_value_2"
   ConvertTo-Json $test_hash
}

function set_hash_of_arrays_test {
   $test_hash = @{}
   set_hash_of_arrays $test_hash "test_key" "test_value_1"
   set_hash_of_arrays $test_hash "test_key" "test_value_2"
   ConvertTo-Json $test_hash
}

function set_nested_hash {
  param (
      [Parameter(Mandatory = $true)][hashtable]$hash = $null,
      [Parameter(Mandatory = $true)][string[]]$keys = $null,
      [Parameter(Mandatory = $true)]$value = $null,
      $opt = $null
   )
   # we need a self-initialized hash of arrays. therefore, we implement this function
   # https://powershell.org/forums/topic/working-with-hash-of-arrays/
   $count = $keys.Count
   $chop1 = $count -1 
   foreach ($key in $keys[0..$chop1]) {
      if (!$hash[$key]) {
         $hash[$key] = @{}
      }
      $hash = $hash[$key]
   }
   $hash[$keys[-1]] = $value   
}

function get_nested_hash {
  param (
      [Parameter(Mandatory = $true)][hashtable]$hash = $null,
      [Parameter(Mandatory = $true)][string []]$keys = $null,
      $opt = $null
   )
   $count = $keys.Count
   $chop1 = $count -1 
   foreach ($key in $keys[0..$chop1]) {
      if (!$hash[$key]) {
         return $null
      }
      $hash = $hash[$key]
   }
   return $hash[$keys[-1]]
}

function set_nested_hash_test {
   $test_hash = @{}
   set_nested_hash $test_hash @("a1", "b1") "value1"
   set_nested_hash $test_hash @("a2", "b2") "value2"
   ConvertTo-Json $test_hash
   if ($test_hash["a3"]) {Write-Host $test_hash["a3"] } else {Write-Host "not exist"}
   if ($test_hash["a3"]["b3"]) {Write-Host $test_hash["a3"]["b3"] } else {Write-Host "not exist"} # this should fail
   get_nested_hash $test_hash @("a3", "b3")
   get_nested_hash $test_hash @("a2", "b2")
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
