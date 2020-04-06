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

$AsciiEncoding = new-object System.Text.AsciiEncoding
$BufferSize = 4*1024*1024
$buffer = new-object System.Byte[] $BufferSize
$encoding = new-object System.Text.AsciiEncoding
$homedir = $HOME


function send_text {
   param (
      [Parameter(Mandatory = $true)]$writer = $null,
      [Parameter(Mandatory = $true)]$text = $null
   )

   $writer.Write([system.Text.Encoding]::Default.GetBytes($text))
}


function is_allowed {
   param (
      [Parameter(Mandatory = $true)][string] $string = $null,
      [Parameter(Mandatory = $true)][hashtable]$AllowDenyPatterns = $null
   )

   # handle deny_patterns
   if ($AllowDenyPatterns["deny"]) {
      foreach ($pattern in $AllowDenyPatterns["deny"]) {
         if ($string -match $pattern) {
            Write-Verbose "$string is denied by $pattern"
            return $false
         }
      }
   }
   
   # handle allow_patterns
   if ($AllowDenyPatterns["allow"]) {
      foreach ($pattern in $AllowDenyPatterns["allow"]) {
         if ($string -match $pattern) {
            Write-Verbose "$string is denied by $pattern"
            return $true
         }
      }
   }

   return $true
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

   $tcpStream = $tcpConnection.GetStream()
   $reader = New-Object System.IO.BinaryReader($tcpStream)
   $writer = New-Object System.IO.BinaryWriter($tcpStream)

   $socket = $null
   if ($role -eq "server") {
      $socket = $tcpConnection.Client
   } else {
      $socket = $tcpConnection.Server
   }

   # unblock socket before reading
   $socket.Blocking = $false

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
            continue
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

   Write-Verbose "remote_tree = $(ConvertTo-Json $remote_tree)"

   Write-Host "$(get_timestamp) building local_tree using paths: $local_paths_string";
   Write-Host "$(get_timestamp) relative path base is homedir=$homedir";

   $local_paths = $local_paths_string -split "[|]"

   # $Matches is a reserved powershell var. a good crap. Therefore, we had to use $matches2
   $matches2 = @()
   if ($match_string -ne "") {
      $matches2 = $match_string -split "`n"
   }

   $excludes = @()
   if ($exclude_string -ne "") {
      $excludes = $exclude_string -split "`n"
   }

   [hashtable]$local_tree,[hashtable]$other = @(build_dir_tree $local_paths @{ RelativeBase=$homedir;
                                                                               matches2=$matches2; 
                                                                               excludes=$excludes; 
                                                                               AllowDenyPatterns = @{}
                                                                              })
   
   Write-Verbose "local_tree  = $(ConvertTo-Json  $local_tree)"
   Write-Verbose "maxsize = $maxsize"

   $deletes = @()
   $change_by_file = @{}
   $diff_by_file = @{}
   $mtimes = @()
   $warns = @()
   $RequiredSpace = 0
   $need_mtime_reset = @{}
   $need_cksums = @()

   if ($other["errors"]) {
      $warns += $other["errors"]
   }

   $back_exists_on_local = @{}
   foreach ($k in $local_tree.keys) {
      $back = get_nested_hash $local_tree @($k, 'back')
      # if (0) { Write-Host $true } else {Write-Host $false}
      # if ("") { Write-Host $true } else {Write-Host $false}
      # if ("0") { Write-Host $true } else {Write-Host $false}
      if (! $back) {
         continue
      }
      $back_exists_on_local[$back] = $true
   }

   if ($other["skipped_back"]) {
      foreach ($back in $other["skipped_back"].keys) {
         $back_exists_on_local[$back] = $true
         $warns += "skipped $back`: $(get_nested_hash $other @("skipped_back", $back))"
      }
   }

   # compare localtree with remote_tree
   foreach ($k in @($remote_tree.Keys|sort)) {
      if (! $local_tree[$k]) {
         # if the back dir is not shown in server side at all, don't delete it on
         # client side.
         # for example, assume client command is
         #    $0 client host port a b
         # if 'a' doesn't exist on the server side, we should not delete b/a on the
         # client side

         $back = get_nested_hash $remote_tree @($k, 'back')

         if ($back_exists_on_local[$back]) {
            $deletes += $k

            if ($k -match '^(.+)/') {
               $parent_dir = $Matches[1]
               $need_mtime_reset[$parent_dir] = $true
            }
         }
      }
   }

   # we sort reverse so that files come before their parent dir. This way enables
   # us to copy some (not have to be all) files under a dir
   foreach ($k in @($local_tree.Keys|sort -descending)) {
      $skipped_message = get_nested_hash $local_tree @($k, 'skip')
      if ($skipped_message) {
         $warns += "skipped $k`: $skipped_message"
         continue
      }

      $remote_size    = get_nested_hash $remote_tree @($k, 'size'   )
      $remote_type    = get_nested_hash $remote_tree @($k, 'type'   )
      $remote_test    = get_nested_hash $remote_tree @($k, 'test'   )      
      $remote_mtime   = get_nested_hash $remote_tree @($k, 'mtime'  )
      $remote_mode    = get_nested_hash $remote_tree @($k, 'mode'   )
      $remote_winmode = get_nested_hash $remote_tree @($k, 'winmode')

       $local_size    = get_nested_hash  $local_tree @($k, 'size'   )      
       $local_type    = get_nested_hash  $local_tree @($k, 'type'   )   
       $local_test    = get_nested_hash  $local_tree @($k, 'test'   )      
       $local_mtime   = get_nested_hash  $local_tree @($k, 'mtime'  )
       $local_mode    = get_nested_hash  $local_tree @($k, 'mode'   ) 
       $local_winmode = get_nested_hash  $local_tree @($k, 'winmode')     

      if (!$remote_tree[$k]) {
         # remote is missing this file
         if ($local_size) {
            if ($maxsize -ge 0 -and $RequiredSpace+$local_size -gt $maxsize) {
               Write-Host "$(get_timestamp) size cutoff before $k`: RequiredSpace+local_size($RequiredSpace+$local_size) > maxsize($maxsize)"
               break
            }
            $RequiredSpace += $local_size
         }
         $change_by_file[$k] = "add"

         if ($k -match '^(.+)/') {
            $parent_dir = $Matches[1]
            $need_mtime_reset[$parent_dir] = $true
         }

         if ($local_type -eq 'dir') {
            # We don't tar dir because that would tar up all files under dir.
            # But the problem with this approach is that the dir mode
            # (permission) is then not recorded in the tar file. We will have
            # to keep and send the mode information separately (from the tar file)
            $modes += $k
         }

         continue
      }

      if ( $remote_type -ne $local_type) {
         $deletes += $k

         if ($local_size) {
            if ($maxsize -ge 0 -and $RequiredSpace+$local_size -gt $maxsize) {
               Write-Host "$(get_timestamp) size cutoff before $k`: RequiredSpace+local_size($RequiredSpace+$local_size) > maxsize($maxsize)"
               break
            }
            $RequiredSpace += $local_size
         }

         $change_by_file[$k] = "newType"

         if ( $local_type -eq 'dir') {
            # We don't tar dir because that would tar up all files under dir.
            # But the problem with this approach is that the dir mode
            # (permission) is then not recorded in the tar file. We will have
            # to keep and send the mode information separately (from the tar file)
            $modes += $k
         }

         continue
      }

      # both sides are same kind type: file, dir, or link
      if ( $local_type -ne 'link') {
         if ( $remote_winmode -ne $local_winmode ) {
            if (!$remote_winmode) {
                # remote is not a windows machine, use $remote_mode.
                # we can only compare $local_winmode's read-only bit with $remote_mode's user's write bit
                # "darhsl" vs "0755"
                $remote_writeable = ($remote_mode    -match "^.[2367]")
                 $local_writeable = ( $local_winmode -match "^..r")
                if ($remote_writeable -ne $local_writeable) {
                   $modes +=$k
                }
            } else {
                $modes += $k
            }
         }
      }

      # note: dir and link's sizes are hard-coded, so they will always equal.
      # therefore, we are really only compares file's sizes.
      # that is, only files can have different sizes.

      if ( $remote_size -ne $local_size ) {
         # only files can reach here
         if ($local_size) {
            if ($maxsize -ge 0 -and $RequiredSpace+$local_size -gt $maxsize) {
               Write-Host "$(get_timestamp) size cutoff before $k`: RequiredSpace+local_size($RequiredSpace+$local_size) > maxsize($maxsize)"
               break
            }
            $RequiredSpace += $local_size
         }

         $change_by_file[$k] = "update"
         $diff_by_file[$k] = $true # files are diff'able

         continue
      }
     
      # compare {test} if it is populated
      # because dir's {test} and link's {test} are hardcoded, we are really only compare files,

      if (!$local_test-and !$remote_test) {
         # if both missing tests, we compare mtime first
         # for fast check (default), if size and mtime match, then no need to update.
         # for deep check, or when mtime not matching (but size matching), resort to
         # cksum.

         if ( $remote_mtime -ne $local_mtime) {
            $need_cksums += $k
            $need_mtime_reset[$k] = $true
         } elseif ($deep_check -eq "1") {
            # $deep_check= "0" or $deep_check= "1"
            $need_cksums += $k
         }
      } elseif ( !$local_test -or !$remote_test) {
         # we reach here if only one test is missing.
         # note: if both tests missing, the logic above would take care of it.
         # not sure what situation will lead us here yet

         $change_by_file[$k] = "update"
      } elseif ($local_test -ne $remote_test) {
         # now both tests exist, we can safely compare
         # not sure what situation will lead us here yet. (we should never reach here)

         $change_by_file[$k] = "update"
      } else {
         # $local_test -eq $remote_test
         if ($remote_mtime -ne $local_mtime) {
            $need_mtime_reset[$k] = $true
         }
      }
   }

   # block socket before writing
   $socket.Blocking = $true

   $need_cksums_string = "<NEED_CKSUMS>" + ($need_cksums -join "`n") + "</NEED_CKSUMS>"
   Write-Host "$(get_timestamp) sending need_cksums request to remote: $($need_cksums.count) items"
   $writer.Write("$need_cksums_string`n")
   $writer.Flush()

   Write-Host "$(get_timestamp) collecting local cksums: $($need_cksums.count) items"
   $local_cksum_by_file = get_cksums($need_cksums, $local_tree)

   # unblock socket before reading
   $socket.Blocking = $false

   Write-Host "$(get_timestamp) waiting for remote cksums results"
   
}


function build_dir_tree {
   param (
      [Parameter(Mandatory = $true)][string []]$paths = $null,
      [hashtable]$opt = $null
   )

   $AllowDenyPatterns = @{}
   if ($opt["AllowDenyPatterns"]) {
      $AllowDenyPatterns = $opt["AllowDenyPatterns"]
   }
   
   # to get UNIX-style mtime, which seconds from epoc time.
   # https://stackoverflow.com/questions/4192971/in-powershell-how-do-i-convert-datetime-to-unix-time
   $unixEpochStart = new-object DateTime 1970,1,1,0,0,0,([DateTimeKind]::Utc)
   # seconds from epoc to now
   # [int]([DateTime]::UtcNow - $unixEpochStart).TotalSeconds

   $old_cwd = $pwd   # save pwd as we keep changing dir later
   $tree = @{}
   $other = @{}

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
         if ( ($p -match "^[a-zA-Z]:[/\\]") -or ($p -match "^[/\\]") ) {
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
            write-host "$(get_timestamp) $message"
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

         if ($abs_path -match '^[/\\]+$') {
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

         if ($abs_path -match '^(.*[/\\])(.+)') {
            $front,$back = $Matches[1],$Matches[2]
         } else {
            Write-Error "unexpected path $abs_path"
            exit 1
         }

         if (!(is_allowed $abs_path $AllowDenyPatterns)) {
            set_nested_hash $other @("skipped_back", $back) "denied"
            continue
         }

         Write-Host "cd '$front'"
         cd $front
         if (!$?) {
            exit 1
         }

         <#
          foreach ($f in @(Get-ChildItem -Recurse tmp)) { ConvertTo-Json $f}
         
          https://stackoverflow.com/questions/41658770/determining-object-type
          foreach ($f in @(Get-ChildItem -Recurse tmp)) { write-host "$($f.FullName) $($f.GetType())"}
          C:\users\william\tmp\ps1 System.IO.DirectoryInfo
          C:\users\william\tmp\space in name System.IO.DirectoryInfo
          C:\users\william\tmp\ps1\List-Exe.ps1 System.IO.FileInfo
          BaseType is System.IO.FileSystemInfo

          foreach ($f in @(Get-ChildItem -Recurse tmp\ps1\List-Exe.ps1)) { ConvertTo-Json $f}
          foreach ($f in @(Get-ChildItem -Recurse -Directory tmp)) { ConvertTo-Json $f}
          foreach ($f in @(Get-ChildItem -Recurse tmp)) { write-host "$($f.DirectoryName)\$($f.Name) $($f.LastWriteTime)"}
         
          foreach ($f in @(Get-ChildItem -Recurse tmp)) { 
             write-host "$($f.FullName) $($f.Mode) $($f.length) $($f.LastWriteTime) PSIsContainer=$($f.PSIsContainer) LinkType=$($f.LinkType) Target=$($f.Target)"}
         
          Get-ChildItem -Recurse tmp | wheres FullName match 'tpnc'
         #>

         # how to read Mode
         # https://stackoverflow.com/questions/4939802/what-are-the-possible-mode-values-returned-by-powershells-get-childitem-cmdle
         # d - Directory
         # a - Archive
         # r - Read-only
         # h - Hidden
         # s - System
         # l - Reparse point, symlink, etc.

         # C:\users\william\tmp\space in name d-----  04/03/2020 23:03:33 PSIsContainer=True LinkType=
         # C:\users\william\tmp\ps1\List-Exe.ps1 -a---- 85 03/22/2020 10:34:15 PSIsContainer=False LinkType=

         $file_count = 0
         :FILES foreach ($item in @(Get-ChildItem -Recurse $back)) {            
            $file_count ++
            if ($file_count % 10000 -eq 0) {
               Write-Host "$(get_timestamp) checked $file_count files"
            }

            $f = $item.FullName

            if ($opt["matches2"] -and $opt["matches2"].count -ne 0) {
               $matched = $false
               # $hash_of_array = @{ 'a'= @(1,2,3)}
               # ConvertTo-Json $hash_of_array['a']
               foreach ($p in $opt["matches2"]) {
                  if ($f -match $p) {
                     $matched = $true
                     last
                  }
               }
               if (!$matched) {
                  continue
               }
            }
         
            if ($opt["excludes"] -and $opt["excludes"].count -ne 0) {
               foreach ($p in $opt["excludes"]) {
                  if ($f -match $p) {
                     continue FILES
                  }
               }
            }  

            if (!(is_allowed $f $AllowDenyPatterns) ) {
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
            set_nested_hash $tree @($f, 'front') $front

            # $wintime = (Get-Item tmp\ps1\List-Exe.ps1).LastWriteTime
            $wintime = $item.lastWriteTime
            $mtime = [int]($wintime - $unixEpochStart).TotalSeconds   # UNIX style, total seconds from epoc
            set_nested_hash $tree @($f, 'mtime') $mtime

            $type = $null
            $size = 0
            if ($item.LinkType) {
               $type = "link"
               $size = 128   #hard coded
               set_nested_hash $tree @($f, 'test') $item.Target
            } elseif ($item.PSIsContainer) {
               $type = "dir"
               $size = 128   # hard coded 
               set_nested_hash $tree @($f, 'test') 'dir' # hard coded, means no test
            } else {
               # todo: there may be other unknown file types
               $type = "file"
               $size = $item.Length
               # cksum is delayed because it is too time-consuming
               # set_nested_hash $tree @($f, 'test') (cksum $f) 
            }
            set_nested_hash $tree @($f, 'size') $size
            set_nested_hash $tree @($f, 'type') $type

            $winmode = $item.Mode    # windows mode "darhsl"
            $mode    = $null         # unix    mode "drwxrwxrwx"
            if ($winmode -match '^..r') {
               # read-only
               if ($type -eq 'dir') {
                  $mode = "0500"
               } else {
                  $mode = "0400"
               }
            } else {
               # writable
               if ($type -eq 'dir') {
                  $mode = "0700"
               } else {
                  $mode = "0600"
               }
            }
            set_nested_hash $tree @($f, 'winmode') $winmode
            set_nested_hash $tree @($f,    'mode')    $mode      
            
            #ConvertTo-Json $tree     
         }
         Write-Host "$(get_timestamp) checked $file_count files in total"
      }  
   }

   cd $old_cwd

   return @($tree, $other)
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

<#
   $test_hash = @{}
   set_hash_of_arrays $test_hash "test_key" "test_value_1"
   set_hash_of_arrays $test_hash "test_key" "test_value_2"
   ConvertTo-Json 

   $array = @()
   # the following two are the same
   $array += $test_hash["test_key"]
   $array += @($test_hash["test_key"])
#>

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
   $chop1 = $count-2
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
   $chop1 = $count-2 
   foreach ($key in $keys[0..$chop1]) {
      if (!$hash[$key]) {
         return $null
      }
      $hash = $hash[$key]
   }
   return $hash[$keys[-1]]
}

<#
   $test_hash = @{}
   set_nested_hash $test_hash @("a1", "b1") "value1"
   set_nested_hash $test_hash @("a2", "b2") "value2"
   ConvertTo-Json $test_hash
   if ($test_hash["a3"]) {Write-Host $test_hash["a3"] } else {Write-Host "not exist"}
   if ($test_hash["a3"]["b3"]) {Write-Host $test_hash["a3"]["b3"] } else {Write-Host "not exist"} # this should fail
   get_nested_hash $test_hash @("a3", "b3")
   get_nested_hash $test_hash @("a2", "b2")
#>


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
             
             for ($i=0; $i -lt $num_patterns; $i++) {
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
[uint64 []]$array2 = @('0xFFFFFFFF', '0x1')
[uint64 []]$array2 = '0xFFFFFFFF','0x1'
$array2.getType()
$array2[0].getType()
#>

[uint64 []]$crctab = @(
   '0x00000000',
   '0x04c11db7', '0x09823b6e', '0x0d4326d9', '0x130476dc', '0x17c56b6b',
   '0x1a864db2', '0x1e475005', '0x2608edb8', '0x22c9f00f', '0x2f8ad6d6',
   '0x2b4bcb61', '0x350c9b64', '0x31cd86d3', '0x3c8ea00a', '0x384fbdbd',
   '0x4c11db70', '0x48d0c6c7', '0x4593e01e', '0x4152fda9', '0x5f15adac',
   '0x5bd4b01b', '0x569796c2', '0x52568b75', '0x6a1936c8', '0x6ed82b7f',
   '0x639b0da6', '0x675a1011', '0x791d4014', '0x7ddc5da3', '0x709f7b7a',
   '0x745e66cd', '0x9823b6e0', '0x9ce2ab57', '0x91a18d8e', '0x95609039',
   '0x8b27c03c', '0x8fe6dd8b', '0x82a5fb52', '0x8664e6e5', '0xbe2b5b58',
   '0xbaea46ef', '0xb7a96036', '0xb3687d81', '0xad2f2d84', '0xa9ee3033',
   '0xa4ad16ea', '0xa06c0b5d', '0xd4326d90', '0xd0f37027', '0xddb056fe',
   '0xd9714b49', '0xc7361b4c', '0xc3f706fb', '0xceb42022', '0xca753d95',
   '0xf23a8028', '0xf6fb9d9f', '0xfbb8bb46', '0xff79a6f1', '0xe13ef6f4',
   '0xe5ffeb43', '0xe8bccd9a', '0xec7dd02d', '0x34867077', '0x30476dc0',
   '0x3d044b19', '0x39c556ae', '0x278206ab', '0x23431b1c', '0x2e003dc5',
   '0x2ac12072', '0x128e9dcf', '0x164f8078', '0x1b0ca6a1', '0x1fcdbb16',
   '0x018aeb13', '0x054bf6a4', '0x0808d07d', '0x0cc9cdca', '0x7897ab07',
   '0x7c56b6b0', '0x71159069', '0x75d48dde', '0x6b93dddb', '0x6f52c06c',
   '0x6211e6b5', '0x66d0fb02', '0x5e9f46bf', '0x5a5e5b08', '0x571d7dd1',
   '0x53dc6066', '0x4d9b3063', '0x495a2dd4', '0x44190b0d', '0x40d816ba',
   '0xaca5c697', '0xa864db20', '0xa527fdf9', '0xa1e6e04e', '0xbfa1b04b',
   '0xbb60adfc', '0xb6238b25', '0xb2e29692', '0x8aad2b2f', '0x8e6c3698',
   '0x832f1041', '0x87ee0df6', '0x99a95df3', '0x9d684044', '0x902b669d',
   '0x94ea7b2a', '0xe0b41de7', '0xe4750050', '0xe9362689', '0xedf73b3e',
   '0xf3b06b3b', '0xf771768c', '0xfa325055', '0xfef34de2', '0xc6bcf05f',
   '0xc27dede8', '0xcf3ecb31', '0xcbffd686', '0xd5b88683', '0xd1799b34',
   '0xdc3abded', '0xd8fba05a', '0x690ce0ee', '0x6dcdfd59', '0x608edb80',
   '0x644fc637', '0x7a089632', '0x7ec98b85', '0x738aad5c', '0x774bb0eb',
   '0x4f040d56', '0x4bc510e1', '0x46863638', '0x42472b8f', '0x5c007b8a',
   '0x58c1663d', '0x558240e4', '0x51435d53', '0x251d3b9e', '0x21dc2629',
   '0x2c9f00f0', '0x285e1d47', '0x36194d42', '0x32d850f5', '0x3f9b762c',
   '0x3b5a6b9b', '0x0315d626', '0x07d4cb91', '0x0a97ed48', '0x0e56f0ff',
   '0x1011a0fa', '0x14d0bd4d', '0x19939b94', '0x1d528623', '0xf12f560e',
   '0xf5ee4bb9', '0xf8ad6d60', '0xfc6c70d7', '0xe22b20d2', '0xe6ea3d65',
   '0xeba91bbc', '0xef68060b', '0xd727bbb6', '0xd3e6a601', '0xdea580d8',
   '0xda649d6f', '0xc423cd6a', '0xc0e2d0dd', '0xcda1f604', '0xc960ebb3',
   '0xbd3e8d7e', '0xb9ff90c9', '0xb4bcb610', '0xb07daba7', '0xae3afba2',
   '0xaafbe615', '0xa7b8c0cc', '0xa379dd7b', '0x9b3660c6', '0x9ff77d71',
   '0x92b45ba8', '0x9675461f', '0x8832161a', '0x8cf30bad', '0x81b02d74',
   '0x857130c3', '0x5d8a9099', '0x594b8d2e', '0x5408abf7', '0x50c9b640',
   '0x4e8ee645', '0x4a4ffbf2', '0x470cdd2b', '0x43cdc09c', '0x7b827d21',
   '0x7f436096', '0x7200464f', '0x76c15bf8', '0x68860bfd', '0x6c47164a',
   '0x61043093', '0x65c52d24', '0x119b4be9', '0x155a565e', '0x18197087',
   '0x1cd86d30', '0x029f3d35', '0x065e2082', '0x0b1d065b', '0x0fdc1bec',
   '0x3793a651', '0x3352bbe6', '0x3e119d3f', '0x3ad08088', '0x2497d08d',
   '0x2056cd3a', '0x2d15ebe3', '0x29d4f654', '0xc5a92679', '0xc1683bce',
   '0xcc2b1d17', '0xc8ea00a0', '0xd6ad50a5', '0xd26c4d12', '0xdf2f6bcb',
   '0xdbee767c', '0xe3a1cbc1', '0xe760d676', '0xea23f0af', '0xeee2ed18',
   '0xf0a5bd1d', '0xf464a0aa', '0xf9278673', '0xfde69bc4', '0x89b8fd09',
   '0x8d79e0be', '0x803ac667', '0x84fbdbd0', '0x9abc8bd5', '0x9e7d9662',
   '0x933eb0bb', '0x97ffad0c', '0xafb010b1', '0xab710d06', '0xa6322bdf',
   '0xa2f33668', '0xbcb4666d', '0xb8757bda', '0xb5365d03', '0xb1f740b4'
)

$CksumBufferSize = 4*1024*1024
$CksumBuffer = new-object System.Byte[] $CksumBufferSize

function cksum {
   param (
      [Parameter(Mandatory = $true)][string]$file = $null,
      $opt = $null
   )

   [uint64]$cksum = 0
   $size =0

   $ifd = $null
   try   { $ifd = [System.IO.File]::OpenRead($file) }
   catch { Write-Host $_; exit 1 } 

   #Set-PsDebug -Trace 1
   while($n = $ifd.Read($CksumBuffer, 0, $CksumBufferSize)) {
      Write-Host "one round"
      $size += $n

      for ($i=0; $i -lt $n; $i++) {
         $c = $CksumBuffer[$i]
         $index = (0xff -band ($cksum -shr 24)) -bxor $c
         #Write-Host "index=$index"
         $cksum = ([uint64]'0xffffffff' -band ($cksum -shl 8)) -bxor $crctab[$index]
      }
   }
   #Set-PsDebug -Trace 0
   $ifd.close()

   Write-Host "size=$size, cksum=$cksum"

   # Extend with the length of the data
   while ($size -ne 0) {
      $c = $size -band 0xFF;
      $size = $size -shr 8;
      $cksum = ([uint64]'0xFFFFFFFF' -band ($cksum -shl 8)) -bxor $crctab[(0xFF -band ($cksum >> 24)) -bxor $c];

      Write-Host "size=$size, cksum=$cksum"
   }

   $cksum = (-bnot $cksum) -band [uint64]'0xffffffff'

   return $cksum
}


cksum C:\Users\william\tmp\ps1\List-Exe.ps1

exit 1


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

   if (!$remainingArgs) {
      usage("wrong numnber of args")
   }

   $local_dir= $null
   $remote_dirs = $null
   if (!$reverse) {
       # tpdist server port
      if ($remainingArgs.count -ne 2) {
         usage("wrong numnber of args")
      }
   } else {
      # tpdist -reverse server port remote_dir ... local_dir
      if ($remainingArgs.count -lt 4) {
         usage("wrong numnber of args")
      }

      $local_dir = $remainingArgs[-1]
      $remote_dirs = $remainingArgs[3..($remainingArgs.count-2)]
      write-verbose "remote_dirs=$remote_dirs, size=$($remote_dirs.count)"
      write-verbose "local_dir=$local_dir"
   }

   $listener_port = $remainingArgs[1]
   write-verbose "listener_port=$listener_port"

   $listener=new-object System.Net.Sockets.TcpListener([system.net.ipaddress]::any, $listener_port)

   if (-not $listener) {
      exit 1
   }
   
   # don't use it now. if this is set, the socket will keep listen after the cmd terminates.
   #$listener.Server.SetSocketOption("Socket", "ReuseAddress", 1)

   try   { $listener.start()     }
   catch { Write-Host $(get_timestamp) $_; exit 1 }
   
   Write-Host $(get_timestamp) "listener started at port $listener_port"

   # $listener | Get-Member

   $tcpConnection = $null

   while ($true) { 
      if ($listener.Pending()) {
         $tcpConnection = $listener.AcceptTcpClient()
         break;
      }
      sleep 1
   }

   Write-Host $(get_timestamp) "accepted client $($tcpConnection.client.RemoteEndPoint.Address):$($tcpConnection.client.RemoteEndPoint.Port)."

   # we only want to accept one client; therefore, close the listener now.
   # $listener.stop()

   if (!$reverse) {
      #Write-Host ($tcpConnection | Format-Table|Out-String)
      #Write-Host $tcpConnection
      #$tcpConnection |Get-Member
      #$tcpConnection.Client |Get-Member

      to_be_pulled $tcpConnection
   } else {    
      to_pull $tcpConnection $remote_dirs $local_dir
   }

   $tcpConnection.Close()
} else {
   # this is client

   if (!$remainingArgs) {
      usage("wrong numnber of args")
   }

   $remote_dirs = $null
   $local_dir   = $null

   if ($reverse) {
      if ($remainingArgs.count -ne 2) {
         usage("wrong numnber of args")
      }
   } else {
      if ($remainingArgs.count -lt 5) {
         usage("wrong numnber of args")
      }

      $local_dir = $remainingArgs[-1]
      $remote_dirs = $remainingArgs[3..($remainingArgs.count-2)]
      write-verbose "remote_dirs=$remote_dirs, size=$($remote_dirs.count)"
      write-verbose "local_dir=$local_dir"
   }

   $remote_host,$remote_port = $remainingArgs[1..2]
   write-verbose "remote_host=$remote_host"
   write-verbose "remote_port=$remote_port"

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
