[CmdletBinding(PositionalBinding = $false)] param(
    [switch]$v = $false,
    [Alias("r")] [switch]$reverse = $false,
    [Alias("n")] [switch]$dryrun = $false,
    [Alias("d")] [switch]$diff = $false,
    [switch]$KeepTmpFile = $false,
    [Alias("m","matches")] [string []]$matches2 = $null,# $Matches is a reserved word, so we use $matches2
    [Alias("x")] [string []]$excludes = $null,
    [Alias("sz")] [switch]$sevenZip = $false,
    [switch]$tpTar = $false,
    [int]$timeout = 300,# expect will time out if pattern not matched witin this much time
    [Alias("idle")] [int]$maxidle = 600,# listener will quit after this much time of idle
    [int]$maxsize = -1,
    [switch]$deep = $false,
    [string]$allowhost = $null,
    [string]$allowfile = $null,
    [string]$denyhost = $null,
    [string]$denyfile = $null,
    [Alias("enc")] [string]$encrypt_key = $null,
    #[Parameter(Mandatory = $true, position=0)][string]$role,
    [Parameter(position = 0)] [string]$role = "unknown",
    [Parameter(ValueFromRemainingArguments = $true)] $remainingArgs = $null
)

Set-StrictMode -Version Latest
#Set-PsDebug -Trace 1

if ($v) {
    $verbosePreference = "Continue"
}

$version = "7.0"

Write-Verbose "version = $version"

$version_split = $version -split "[.]"
$expected_peer_protocol = $version_split[0]
Write-Verbose "`$expected_peer_protocol = $expected_peer_protocol"

$AsciiEncoding = New-Object System.Text.AsciiEncoding
$BufferSize = 4 * 1024 * 1024
$buffer = New-Object System.Byte[] $BufferSize
$encoding = New-Object System.Text.AsciiEncoding

$homedir = $HOME.Replace('\','/');
Write-Verbose "homedir = $homedir"

# https://docs.microsoft.com/en-us/dotnet/api/system.io.path.gettemppath?view=netframework-4.8&tabs=windows
# C:\Users\UserName\AppData\Local\Temp\ 
$tmpdir = "$([System.IO.Path]::GetTempPath())\tpsup".Replace('\','/');
Write-Verbose "tmpdir = $tmpdir"

$prog = ($PSCommandPath.Split('/\'))[-1]
Write-Verbose "prog = $prog"

$scriptdir = (Split-Path -Parent $PSCommandPath).Replace('\','/');
Write-Verbose "scriptdir = $scriptdir"

# to get UNIX-style mtime, which seconds from epoc time.
# https://stackoverflow.com/questions/4192971/in-powershell-how-do-i-convert-datetime-to-unix-time
$unixEpochStart = New-Object DateTime 1970,1,1,0,0,0,([DateTimeKind]::Utc)
# seconds from epoc to now, ie, mtime
# [int]([DateTime]::UtcNow - $unixEpochStart).TotalSeconds

# we cannot copy root dir
# root dirs: /, //, C:, C:/, /cygdrive/c, /cygdrive/c/, or with \
# note: ` is escape for powershell, \ is escape for regex
$root_dir_pattern = '^[a-zA-Z]:[\\/]*$|^[\\/]+$|^[\\/]+cygdrive[\\/]+[^\\/]+[\\/]*$';
$abs_pattern = '^[a-zA-Z]:[\\/]|^[\\/]+|^[\\/]+cygdrive[\\/]+[^\\/]+[\\/]';

$old_pwd = $pwd.ToString().Replace('\','/');
Write-Verbose "saved_pwd=$old_pwd"

function add_path {
    param([Parameter(Mandatory = $true)] [string]$var,
        [Parameter(Mandatory = $true)] [string]$value
    )

    [string]$old_string = (Get-Item -Path "Env:$var").Value
    $parts = $old_string -split ';'

    if (!($parts -contains $value)) {
        Write-Verbose "adding to `$Env:PSModulePath: $value"
        $Env:PSModulePath += ";$value"
    }
}

add_path "PSModulePath" $HOME
add_path "PSModulePath" $scriptdir.Replace('/','\')
add_path "PSModulePath" "."    # use '.' to add current path in powershell when unix use empty string ''
add_path "PSModulePath" "$HOME\ps1m\7Zip4Powershell\1.10.0.0"

Write-Verbose ("`$Env:PSModulePath = {0}" -f $Env:PSModulePath)

if ($sevenZip -or $tpTar) {
    [string]$TestCmd = $null
    [string]$Module = $null

    if ($sevenZip) {
        $TestCmd = "Expand-7Zip"
        $Module = "7Zip4PowerShell"
    } else {
        $TestCmd = "TpTar"
        $Module = "TpTar"
    }

    if (-not (Get-Command $TestCmd -ErrorAction Ignore)) {
        Import-Module $Module
    }

    Write-Verbose ("$Module is from {0}" -f (Get-Module $Module).Path)
} else {
    # we must use windows Tar.exe
    if (Get-Command tar.exe -ErrorAction SilentlyContinue) {
        Write-Verbose "we use tar.exe to tar files"
    } else {
        Write-Host "ERROR: cannot find tar.exe. Please try -tpTar or -sevenZip"
        exit 1
    }
}

function usage {
    param([string]$message = $null)

    if ($message) {
        Write-Host $message
    }

    Write-Host "
Usage:

   ${prog} in powershell

   normal mode: server waits to be pulled; client pulls.
     ${prog} server local_port
     ${prog} client remote_host remote_port remote_path1 remote_path2 ... local_dir

   reversed mode: server waits to take in data; client pushes.
     ${prog} server local_port  -reverse remote_port remote_path1 remote_path2 ... local_dir
     ${prog} client remote_host remoe_port -reverse

   If remote path is a relative path, it will be relative to remote user's home dir.
   The current user homedir=$homedir

   to show version
      ${prog} version

Common Swithes

   -v                 verbose mode.

   -KeepTimeFile      default to delete it. tmpdir=$tmpdir

  -r|reverse          server-pull/client-push. default is server-push/client-pull

  -timeout seconds
                      time to wait for peer to finish a transaction, default to 300

  -sz|sevenzip        use 7Zip to handel tar files. default to use tar.exe. Make sure 
                      7Zip4PowerShell/7Zip4PowerShell.psd1 is in `$PSModulePath, `$Home,
                      script dir, or current path

  -tpTar              use TpTar to handel tar files. default to use tar.exe. Make sure 
                      TpTar/TpTar.psm1 is in `$PSModulePath, `$Home, script dir, or 
                      current path.

Passive-side Switches: (To-be Pulled, normal Server state)

   -idle seconds
                      max idle time before close server socket, default to 600

   -allowhost file
   -denyhost file
                      file contains allowed/deny host or ip. one per line,
                      lines stars with # is comment
                      default:
                          `$HOME/.tpsup/tpdist_allowhost.txt
                          `$HOME/.tpsup/tpdist_denyhost.txt

   -allowfile file
   -denyfile file
                      file contains allowed/deny dir or file, one per line,
                      lines stars with # is comment
                      default:
                         `$HOME/.tpsup/tpdist_allowfile.txt
                         `$HOME/.tpsup/tpdist_denyfile.txt

Active-Side Switches: (To Pull, normal Client State)

   -n                 dryrun mode, list the filenames only

   -diff              diff mode. Besides listing file names as in dryrun mode, also
                      run diff if the file is on both sides. This mode will not
                      change any files.

   -maxsize           get up to this much bytes of total update, this is to limit
                      the size of update, meaning will drop some changes.
                      default is -1, meaning no limit.

   -matches  'pattern1', 'pattern2', ... (separated by ',')
                      only files that matching this pattern (Perl RegEx style).
                      can be specified multiple times (in OR logic).

   -excludes 'pattern1', 'pattern2', ... (separated by ',')
                      exclude files that matching this pattern (Perl RegEx style)
                      can be specified multiple times (in OR logic).

   -deep              set to always use cksum to check. Default is fast check: if file size
                      and timestamp matches, we don't use cksum. cksum is time-consumig.

   -maxtry times
                      retry to connect to server, default to 5

   -interval seconds
                       time between each retry, default to 30

Examples:

  as a server
     ${prog}.ps1 server 5555

  as a client
     ${prog}.ps1 client localhost 5555 /cygdrive/c/Users/william/github/tpsup/ps1 tmp 

     ${prog}.ps1 client localhost 5555 'C:/users/william/sitebase/github/tpsup/ps1' 'C:/users/william/sitebase/github/tpsup/kdb' tmp

"
    exit 1
}


function get_timestamp {
    return "{0:yyyyMMdd} {0:HH:mm:ss}" -f (Get-Date)
}

class MyCoder{
    [int]$index = 0 # current char position in $key_str
    [Byte []]$key_array = $null
    [int]$key_length = 0
    [string]$key_str

    MyCoder ([string]$key_str) {
        $this.key_str = $key_str
        if ($key_str) {
            $this.key_array = @([System.Text.Encoding]::Default.GetBytes($key_str))
            $this.key_length = $this.key_array.Length
            $this.index = 0
        }
    }

    [byte []] xor ([byte[]]$plain_bytes,[int]$size) {
        if (!$this.key_str) {
            return [byte[]]$plain_bytes
        }

        $xored_bytes = New-Object 'System.Collections.Generic.List[byte]'

        $i = 0;
        foreach ($byte in $plain_bytes) {
            $i++
            if ($size -ge 0 -and $i -gt $size) {
                break
            }

            $xored_bytes.Add($byte -bxor $this.key_array[$this.index])

            $this.index++
            if ($this.index -eq $this.key_length) {
                $this.index = 0
            }
        }

        return [byte []]$xored_bytes.ToArray()
    }

    # powershell doesn't support optional parameters. we have to delegate
    [byte []] xor ([byte[]]$plain_bytes) {
        return $this.xor($plain_bytes,-1)
    }
}


class MyConn{
    [System.Net.Sockets.TcpClient]$tcpclient = $null
    [System.Net.Sockets.NetworkStream]$stream = $null
    [System.Net.Sockets.Socket]$socket = $null
    [System.IO.BinaryReader]$reader = $null
    [System.IO.BinaryWriter]$writer = $null
    [int]$in_count = 0 # bytes received
    [int]$out_count = 0 # bytes sent
    [string]$key = $null # encrypt key
    [MyCoder]$in_coder = $null # encoder for incoming
    [MyCoder]$out_coder = $null # encoder for outcoming

    MyConn (
        [System.Net.Sockets.TcpClient]$tcpclient,
        [string]$key
    ) {

        $this.tcpclient = $tcpclient
        $this.socket = $tcpclient.Client

        try {
            $this.stream = $tcpclient.GetStream()
        } catch {
            Write-Host $_
            exit 1
        }

        $this.reader = New-Object System.IO.BinaryReader ($this.stream)
        $this.writer = New-Object System.IO.BinaryWriter ($this.stream)
        $this.in_count = 0
        $this.out_count = 0

        $this.key = $key
        $this.in_coder = [MyCoder]::new($key)
        $this.out_coder = [MyCoder]::new($key)
    }
}


function send_text_line {
    param(
        [Parameter(Mandatory = $true)] [MyConn]$myconn,
        [Parameter(Mandatory = $true)] $text
    )

    $line = "$text`n"
    Write-Verbose "   $line"

    $bytes = [System.Text.Encoding]::Default.GetBytes("$text`n")

    $encoded = [byte []]$myconn.out_coder.xor($bytes)

    $myconn.writer.Write($encoded)
    $size = $bytes.Count
    $myconn.out_count += $size
    Write-Verbose "   sent $size byte(s), total=$($myconn.out_count)"
}


function load_access {
    param(
        [Parameter(Mandatory = $true)] $user_specified,
        [hashtable]$opt = $null
    )

    $matrix = @{}

    foreach ($type in @('host','file')) {
        foreach ($access in @('allow','deny')) {
            $key = "${access}${type}"

            $file = $null
            if ($user_specified[$key]) {
                $file = $user_specified[$key]
            } elseif (Test-Path "$homedir/.tpsup/tpdist_$key.txt" -ErrorAction SilentlyContinue) {
                $file = "$homedir/.tpsup/tpdist_$key.txt"
            }

            if ($file) {
                Write-Verbose "reading $file"
                $patterns = @(read_security_file $file)
                if ($patterns) {
                    set_nested_hash $matrix @($type,$access) $patterns
                } else {
                    # why fatal here?
                    # because if a file exists but is empty, for example, if the allow file exists but is
                    # empty, should we allow all or allow none? this becomes ambiguous and prone to error!!
                    Write-Host "FATAL: there is no settings in $file. It may mean 'allow all' or 'deny all'. To avoid ambiguity, either remove file or add settings."
                    exit 1;
                }
            }
        }
    }

    return $matrix;
}


function read_security_file {
    param(
        [Parameter(Mandatory = $true)] $file,
        [hashtable]$opt = $null
    )

    if (!(Test-Path $file)) {
        Write-Host "cannot find $file"
        exit 1
    }

    # https://stackoverflow.com/questions/21310538/get-all-lines-containing-a-string-in-a-huge-text-file-as-fast-as-possible
    # skip blank lines and comment lines
    # trim blanks at beginning and end of lines
    # PS C:\Users\william> @("a","a2")|foreach {$_ -replace ("a", "b")} |foreach {$_ -replace ("2", "3")}
    # b
    # b3
    # but the following didn't work
    # $patterns = @(Get-Content $file | foreach { !($_ -match '^\s*$' -or $_ -match '^\s*#') } | foreach {$_ -replace ('^\s+', '')} | foreach {$_ -replace ('s+$', '')})
    # resort to old style
    $patterns = New-Object System.Collections.Generic.List[System.String]
    $lines = @(Get-Content $file)

    foreach ($l in $lines) {
        # skip blank lines and comment lines
        if ($l -match '^\s*$' -or $l -match '^\s*#') { continue }

        # trim leading and ending blanks
        $l = $l -replace '^\s+',''
        $l = $l -replace '\s+$',''

        $patterns.Add($l)
    }

    return $patterns;
}


function is_allowed {
    param(
        [Parameter(Mandatory = $true)] [string]$string,
        [Parameter(Mandatory = $true)][AllowNull()] [hashtable]$AllowDenyPatterns
    )

    # handle deny_patterns
    if ($AllowDenyPatterns -and $AllowDenyPatterns["deny"]) {
        foreach ($pattern in $AllowDenyPatterns["deny"]) {
            if ($string -match $pattern) {
                Write-Verbose "$string is denied by pattern '$pattern'"
                return $false
            }
        }
    }

    # handle allow_patterns
    if ($AllowDenyPatterns -and $AllowDenyPatterns["allow"]) {
        foreach ($pattern in $AllowDenyPatterns["allow"]) {
            if ($string -match $pattern) {
                Write-Verbose "$string is allowed by pattern '$pattern'"
                return $true
            }
        }
    }

    return $true
}


function to_pull {
    param(
        [Parameter(Mandatory = $true)] [MyConn]$myconn,
        [Parameter(Mandatory = $true)] [string []]$remote_paths,
        [Parameter(Mandatory = $true)] [string]$local_dir,
        [hashtable]$opt = $null
    )

    $dryrun_string = ""
    if ($dryrun -or $diff) {
        $dryrun_string = "dryrun"
    }

    $stream = $myconn.stream
    $reader = $myconn.reader
    $writer = $myconn.writer
    $socket = $myconn.socket
    $tcpclient = $myconn.tcpclient

    # block socket before writing
    $socket.Blocking = $true

    $local_dir.TrimEnd('/\') # remove the trailing /, literal match, no need to escape
    $local_dir_abs = get_abs_path $local_dir

    $local_paths = New-Object System.Collections.Generic.List[System.String]
    foreach ($remote_path in $remote_paths) {
        $remote_path = $remote_path.Replace('\','/').TrimEnd('/')

        if ($remote_path -match "$root_dir_pattern") {
            $message = "cannot copy from root dir: $remote_path"
            Write-Host "ERROR: $message"
            send_text_line $myconn $message
            return
        }

        # get the last component; we will treat it as a subdir right under local_dir
        $remote_path -match '([^/]+)$' | Out-Null
        $back = $Matches[1]

        $local_path = "$local_dir/$back"

        # resolve dir/*csv to dir/a.csv, a/b.csv, ...
        #    example:
        #       $0 client host port /a/b/c/*.csv d
        #    we need to check whether we have d/*.csv

        $globs = @(Resolve-Path -Path $local_path -ErrorAction SilentlyContinue | Select-Object -ExpandProperty "Path")

        # if (!@()) {write-Host "no"}
        if (!$? -or !$globs) { continue }

        foreach ($path in $globs) {
            $local_abs = get_abs_path $path
            if (!$local_abs) { continue }
            Write-Verbose "remote ($remote_path) -> local ($local_path) -> local abs ($local_abs)"
            $local_paths.Add($local_abs)
        }
    }

    Write-Verbose "building local tree using abs_path: $($local_paths -join " "), "
    $local_tree = build_dir_tree $local_paths @{ excludes = $excludes; matches2 = $matches2 }
    Write-Verbose "local_tree = $(ConvertTo-Json $local_tree)"

    # block socket when writing;flush writes manually
    $socket.Blocking = $true

    Write-Host "$(get_timestamp) sending version: $version"
    send_text_line $myconn "<VERSION>$version</VERSION>"

    $paths_string = $remote_paths -join '|'
    Write-Host "$(get_timestamp) sending paths: $paths_string"
    send_text_line $myconn "<PATH>$paths_string</PATH>"

    $deep_number = 0
    if ($deep) { $deep_number = 1 }
    Write-Host "$(get_timestamp) sending deep check flag: $deep_number"
    send_text_line $myconn "<DEEP>$deep_number</DEEP>"

    # https://powershellexplained.com/2017-11-20-Powershell-StringBuilder/
    $local_tree_block = ""
    $local_tree_items = 0
    $skipped = 0
    if ($local_tree) {
        $sb = [System.Text.StringBuilder]::new()

        foreach ($k in @($local_tree.Keys | sort)) {
            $skipped_message = get_nested_hash $local_tree @($k,'skip')
            if ($skipped_message) {
                # don't send skipped file to remote; this way, remote will not
                # tell us to delete them.
                $skipped++
                continue
            }
            $local_tree_items++
            $sb2 = [System.Text.StringBuilder]::new()
            [void]$sb2.Append("key=$k")
            foreach ($attr in @($local_tree[$k].Keys | sort)) {
                # https://stackoverflow.com/questions/7801651/powershell-and-stringbuilder
                # add [void] to avoid unwanted output
                [void]$sb2.Append("|$attr=$($local_tree[$k][$attr])")
            }
            [void]$sb.Append("$($sb2.ToString())`n")
        }
        $local_tree_block = $sb.ToString()
    }
    Write-Host "$(get_timestamp) sending local tree, $local_tree_items items, skipped $skipped items"
    send_text_line $myconn "<TREE>$local_tree_block</TREE>"

    Write-Host "$(get_timestamp) sending maxsize: $maxsize"
    send_text_line $myconn "<MAXSIZE>$maxsize</MAXSIZE>"

    $excludes_string = ""
    if ($excludes) { $excludes_string = $excludes -join "`n" }
    Write-Host "$(get_timestamp) sending excludes: $excludes_string"
    send_text_line $myconn "<EXCLUDE>$excludes_string</EXCLUDE>"

    $matches2_string = ""
    if ($matches2) { $matches2_string = $matches2 -join "`n" }
    Write-Host "$(get_timestamp) sending matches: $matches2_string"
    send_text_line $myconn "<MATCH>$matches2_string</MATCH>"

    $os = Get-CimInstance Win32_OperatingSystem
    $uname = "PowerShell| $($os.Caption) $($os.Version)"
    Write-Host "$(get_timestamp) sending prog|uname: $uname"
    send_text_line $myconn "<UNAME>$uname</UNAME>"

    $writer.Flush()

    # unblock socket when reading
    $socket.Blocking = $false

    $patterns = @('<NEED_CKSUMS>(.*)</NEED_CKSUMS>')

    $captures = @(expect_socket $myconn $patterns @{ ExpectTimeout = $timeout })

    if (!$captures) {
        $reader.Dispose()
        $writer.Dispose()
        $stream.close()
        return
    }
    $need_cksums_string = $captures[0][0]

    $need_cksums = @()
    $cksums_results = New-Object System.Collections.Generic.List[System.String]
    if ($need_cksums_string) {
        $need_cksums = $need_cksums_string -split "`n"

        Write-Host "$(get_timestamp) received cksum requests, $($need_cksums.Count) items. calculating local cksums"

        $local_cksums_by_file = get_cksums $need_cksums $local_tree

        foreach ($f in ($local_cksums_by_file.Keys | sort)) {
            $cksums_results.Add("$local_cksums_by_file[$f] $f")
        }
    } else {
        Write-Host "$(get_timestamp) received cksum requests, 0 items"
    }

    # don't unblock socket when writing; doing so would corrupt data.
    # instead, flush writes manually
    $socket.Blocking = $true

    $cksums_results_string = $cksums_results -join "`n"

    Write-Host "$(get_timestamp) sending cksum results: $($cksums_results.Count) item(s)"
    send_text_line $myconn "<CKSUM_RESULTS>$cksums_results_string</CKSUM_RESULTS>"

    $writer.Flush() # flush data when writes are done.

    Write-Host "$(get_timestamp) waiting instructions from remote ..."

    # unblock socket when reading
    $socket.Blocking = $false

    $patterns = @('<DELETES>(.*)</DELETES>',
        '<MTIMES>(.*)</MTIMES>',
        '<MODES>(.*)</MODES>',
        '<SPACE>(\d+)</SPACE>',
        '<ADDS>(.*)</ADDS>',
        '<WARNS>(.*)</WARNS>')

    $captures = @(expect_socket $myconn $patterns @{ ExpectTimeout = $timeout })

    if (!$captures) {
        $reader.Dispose()
        $writer.Dispose()
        $stream.close()
        return
    }

    $deletes_string = $captures[0][0]
    $mtimes_string = $captures[1][0]
    $modes_string = $captures[2][0]
    $RequiredSpace = [int]$captures[3][0]
    $adds_string = $captures[4][0]
    $warns_string = $captures[5][0]

    # if local_dir doesn't exist yet, we don't mkdir now because if this is a
    # dryrun or diff, then we shouldn't create a dir. we will create it later.
    # But why do we "cd $local_dir_abs" here? because the followed deletes use
    # the relative path; so does diff.

    if (Test-Path -Path $local_dir_abs) {
        Write-Host "$(get_timestamp) cd '$local_dir_abs'"
        cd $local_dir_abs
        if (!$?) { Write-Host "ERROR: cd $local_dir_abs failed"; exit 1 }

        if ($deletes_string) {
            $deletes = @($deletes_string -split "`n")

            $last_delete = $null

            foreach ($d in ($deletes | sort)) {
                if (!$last_delete -or !($d -match "$last_delete")) {
                    # if we already deleted the dir, no need to delete files under it.

                    $cmd = "rm -r -fo '$d'"
                    Write-Host "$dryrun_string $cmd"
                    if (!$dryrun -and !$diff) {
                        rm -r -fo $d
                    }

                    $last_delete = $d;
                }
            }
        }
    }

    $diff_files = New-Object System.Collections.Generic.List[System.String]

    if ($adds_string) {
        $action_by_file = @{};

        $adds = @($adds_string -split "`n")

        foreach ($a in $adds) {
            if ($a -eq '') { continue }

            if ($a -match "^\s*(\S+?) (.+)") {
                $action = $Matches[1]
                $file = $Matches[2]

                if ($action -eq 'update') { $diff_files.Add($file) }

                if ($action_by_file[$file]) { Write-Host "ERROR: $file appeared more than once on remote side" }
                $action_by_file[$file] = $action
            } else {
                $message = "ERROR: unexpected format $a. expecting: (add|update|newType) file"
                Write-Host "$message"
                send_text_line $myconn $message
                $writer.Flush()
                return
            }
        }

        foreach ($f in ($action_by_file.Keys | sort)) {
            Write-Host ("$dryrun_string {0,7} {1}" -f $action_by_file[$f],$f)
        }
    }

    if ($warns_string) {
        $warns = @($warns_string -split "`n")
        foreach ($w in $warns) {
            Write-Host "warning from remote side: $w"
        }
    }

    #(Get-WmiObject win32_logicaldisk | Where-Object {$_.DeviceId -eq 'C:'}).FreeSpace
    # check tmp space
    [string]$tmp_tar_file = $null
    [string]$tmp_diff_dir = $null
    try {
        # use [String] to prevent powershell automatically convert string to Path
        $tmp_tar_file = [string](get_tmp_name $tmpdir $prog @{ chkSpace = ($RequiredSpace * 2) })
    } catch {
        send_text_line $myconn $_.Exception.Message
        $writer.Flush()
        return
    }

    if (!$adds_string) {
        $message = "nothing to add or update"
        Write-Host "$(get_timestamp) $message"
        send_text_line $myconn $message
        # don't return here as we will have other work to do
    } elseif (!$dryrun) {
        # block socket when writing to avoid corrupt data and flush writes manually
        $socket.Blocking = $true

        $message = $null;
        if ($diff) {
            $message = "please send diff"
        } else {
            $message = "please send data"
        }

        Write-Host $message
        send_text_line $myconn $message
        $writer.Flush()

        if ($diff) {
            try {
                # use [String] to prevent powershell automatically convert string to Path
                $tmp_diff_dir = [string]((get_tmp_name $tmpdir $prog @{ chkSpace = ($RequiredSpace * 2) }) + "_dir")
            } catch {
                send_text_line $myconn $_.Exception.Message
                $writer.Flush()
                return
            }

            mkdir $tmp_diff_dir
            if (!$?) { Write-Host "mkdir $tmp_diff_dir failed"; exit 1 }

            cd $tmp_diff_dir
            if (!$?) { Write-Host "mkdir $tmp_diff_dir failed"; exit 1 }
        } else {
            if (!(Test-Path $local_dir_abs)) {
                Write-Host "$(get_timestamp) $dryrun_string mkdir $local_dir_abs"
                if (!$dryrun) {
                    mkdir -p $local_dir_abs
                    if (!$?) { Write-Host "mkdir $local_dir_abs failed"; exit 1 }
                }
            }

            Write-Host "$(get_timestamp) $dryrun_string cd $local_dir_abs"
            if (!$dryrun) {
                cd $local_dir_abs
                if (!$?) { Write-Host "cd $local_dir_abs failed"; exit 1 }
            }
        }

        # unblock socket when reading
        $socket.Blocking = $false

        Write-Host $(get_timestamp) "waiting for data from remote,`n   will write to $tmp_tar_file"

        # create an FileStream for output
        $out_stream = $null
        try { $out_stream = [System.IO.File]::Create($tmp_tar_file) }
        catch { Write-Host $(get_timestamp) $_; exit 1 }

        $tar_size = 0

        while ($tcpclient.Connected) {
            while ($stream.DataAvailable) {
                $size = $stream.Read($buffer,0,$BufferSize)

                if ($size -gt 0) {
                    $tar_size += $size
                    Write-Verbose "received $size byte(s). subtotal tar_size=$tar_size byte(s)"
                    # $out_stream.Write($buffer, 0, $size)
                    #$decoded = xor_encode $buffer 'in' $size
                    $decoded = $myconn.in_coder.xor($buffer,$size)
                    $out_stream.Write($decoded,0,$size)
                } else {
                    # this should happen sometimes but never worked.
                    Write-Host "$(get_timestamp) first time happend. remote closed connection"
                    exit 1
                }
            }

            if (($tcpclient.Client.Poll(1,[System.Net.Sockets.SelectMode]::SelectRead) -and
                    $tcpclient.Client.Available -eq 0)) {
                Write-Host "$(get_timestamp) remote disconnected"
                break
            }

            #start-sleep -Milliseconds 1000
            sleep 1
        }

        $out_stream.Flush()
        $out_stream.Dispose()

        Write-Host "$(get_timestamp) received tar_size = $tar_size"

        if ($tar_size -eq 0) {
            if ($action_by_file.Count -gt 0) {
                Write-Error "$(get_timestamp) file transfer failed. we shouldn't receive 0 size";
                return;
            } else {
                Write-Host "$(get_timestamp) no new file to add"
            }
        } else {
            [string]$cmd = $null
            if ($sevenZip -or $tpTar) {
                if ($sevenZip) {
                    $cmd = "Expand-7Zip $tmp_tar_file $pwd"
                } else {
                    $cmd = "TpTar -x -v -f $tmp_tar_file"
                }

                Write-Host "$(get_timestamp) $cmd"
                # Invoke-Expression is unix-"eval" equivalent
                Invoke-Expression $cmd
                if (!$?) {
                    Write-Host "cmd failed: $cmd"
                    return;
                }
            } else {
                Write-Host "$(get_timestamp) tar -xf $tmp_tar_file"
                # 1. tar -xvf $tmp_tar_file causing error because of '-v'. therefore, use 2 commands instead
                # 2. need to wait external command to finish before remove the $tmp_tar_file, eg, use |Out_Host
                # https://stackoverflow.com/questions/1741490/how-to-tell-powershell-to-wait-for-each-command-to-end-before-starting-the-next
                tar -tf $tmp_tar_file | Out-Host
                tar -xf $tmp_tar_file | Out-Host
            }
        }

        if ($KeepTmpFile) {
            Write-Host "$(get_timestamp) tmp_tar_file $tmp_tar_file is kept"
        } else {
            Write-Verbose "$(get_timestamp) rm tmp_tar_file=$tmp_tar_file"
            Remove-Item $tmp_tar_file
        }

        if ($diff) {
            Write-Verbose "$(get_timestamp) cd '$old_pwd"
            if (!$?) { Write-Host "cd $old_pwd failed"; exit 1 }

            foreach ($relative_path in $diff_files) {
                Write-Host "$(get_timestamp) diff (cat '$tmp_diff_dir/$relative_path') (cat '$local_dir_abs/$relative_path')"
                diff (cat "$tmp_diff_dir/$relative_path") (cat "$local_dir_abs/$relative_path")
            }

            if ($KeepTmpFile) {
                Write-Host "$(get_timestamp) tmp_diff_dir $tmp_diff_dir is kept\n";
            } else {
                cd $old_pwd # get out of the folder before remove it
                Write-Verbose "$(get_timestamp) remove tmp_diff_dir $tmp_diff_dir"
                rm -r -fo $tmp_diff_dir
            }
        }
    }

    if ($mtimes_string) {
        $lines = @($mtimes_string -split "`n")

        foreach ($l in $lines) {
            if ($l -eq '') { continue }

            if ($l -match "^([0-9]+)\s+(\S.*)") {
                $mtime,$f = $Matches[1],$Matches[2]

                $new_LastWriteTimeUtc = $unixEpochStart.AddSeconds([int]$mtime)

                Write-Host "$dryrun_string (Get-Item -Path $f).LastWriteTimeUtc = $new_LastWriteTimeUtc"
                if (!$dryrun -and !$diff) {
                    (Get-Item -Path $f).LastWriteTimeUtc = $new_LastWriteTimeUtc
                }
            } else {
                Write-Host "ERROR: bad mtime format at line: $l"
            }
        }
    }

    if ($modes_string) {
        $lines = @($modes_string -split "`n")

        foreach ($l in $lines) {
            if ($l -eq '') { continue }

            if ($l -match "^(\S+)\s+(\S.*)") {
                $mode,$f = $Matches[1..2]

                Write-Host "don't know how to change mode: $mode,$f"
            } else {
                Write-Host "ERROR: bad mode format at line: $l"
            }
        }
    }
}

function to_be_pulled {
    param(
        [Parameter(Mandatory = $true)] [MyConn]$myconn = $null,
        [hashtable]$opt = $null
    )

    $stream = $myconn.stream
    $reader = $myconn.reader
    $writer = $myconn.writer
    $socket = $myconn.socket
    $tcpclient = $myconn.tcpclient

    Write-Host $(get_timestamp),"waiting information from remote ...`n";

    $patterns = @(
        '<PATH>(.+)</PATH>',
        '<TREE>(.*)</TREE>',
        '<MAXSIZE>([-]?\d+)</MAXSIZE>',
        '<VERSION>(.+)</VERSION>',
        '<EXCLUDE>(.*)</EXCLUDE>',
        '<MATCH>(.*)</MATCH>',
        '<DEEP>(.)</DEEP>',
        '<UNAME>(.+)</UNAME>'
    )

    $captures = @(expect_socket $myconn $patterns @{ ExpectTimeout = $timeout })

    if (!$captures) {
        $reader.Dispose()
        $writer.Dispose()
        $stream.close()
        return
    }

    $local_paths_string = $captures[0][0]
    $remote_tree_block = $captures[1][0]
    $maxsize = [int]$captures[2][0]
    $remote_version = $captures[3][0]
    $exclude_string = $captures[4][0]
    $match_string = $captures[5][0]
    $deep_check = [int]$captures[6][0]
    $uname = $captures[7][0]

    $remote_version_split = $remote_version -split "[.]";
    $peer_protocol = $remote_version_split[0]

    if ($peer_protocol -ne $expected_peer_protocol) {
        $message = "wrong protocol $peer_protocol, we are expecting protocol $expected_peer_protocol. we closed the connection."
        Write-Host "$(get_timestamp) $message"
        send_text_line $myconn $message
        $writer.Flush()
        return
    }

    $check_mode = $false
    if ($uname -match "^Powershell" -or $uname -match "Windows") {
        $check_mode = $true
    }

    Write-Host "$(get_timestamp) remote uname='$uname'. we set check_mode=$check_mode"

    $remote_tree = @{}

    if ($remote_tree_block -ne "") {
        $lines = $remote_tree_block -split "`n"

        foreach ($l in $lines) {
            if (!($l -match "^key=")) {
                continue
            }

            $pairs = $l -split "[|]"
            $branch = @{}
            foreach ($pair in $pairs) {
                $k,$v = $pair -split "=",2
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

    # on to_be_pulled side, we need check access with AllowDenyPatterns.
    # matches and excludes are coming from remote side
    # RelativeBase is coming from command line
    [hashtable]$local_tree = build_dir_tree $local_paths @{ RelativeBase = $homedir;
        matches2 = $matches2;
        excludes = $excludes;
        AllowDenyPatterns = $AccessMatrix['file']
    }
    Write-Verbose "local_tree  = $(ConvertTo-Json  $local_tree)"
    Write-Verbose "maxsize = $maxsize"

    # https://powershell.org/2013/09/powershell-performance-the-operator-and-when-to-avoid-it/
    # powershell's list $a=@() is immutable, meaning, $a.Add("hello") won't work.
    # we have to use $a += "hello" which creates a new list, and is very inefficient.
    # powershell suggests to use 
    # $a = New-Object System.Collections.Generic.List[System.String]
    # $a.Add("hello")
    # $a.Add("world")
    # $a -join "-"

    $deletes = New-Object System.Collections.Generic.List[System.String]
    $change_by_file = @{}
    $diff_by_file = @{}
    $cannot_by_file = @{}
    $modes = New-Object System.Collections.Generic.List[System.String]
    $warns = New-Object System.Collections.Generic.List[System.String]
    $RequiredSpace = 0
    $need_mtime_reset = @{}
    $need_cksums = New-Object System.Collections.Generic.List[System.String]

    # compare localtree with remote_tree
    foreach ($k in @($remote_tree.Keys | sort)) {
        if (!$local_tree[$k]) {
            # if the back dir is not shown in local side at all, don't delete it on
            # remote side.
            # for example, assume remote side runs command as
            #    $0 client host port a b
            # if 'a' doesn't exist on the local side, we (local side) should not tell
            # remote to delete b/a on the remote side
            $back = get_nested_hash $remote_tree @($k,'back')
            if ($local_tree[$back]) {
                $deletes.Add($k)
            }
        }
    }

    # we sort reverse so that files come before their parent dir. This way enables
    # us to copy some (not have to be all) files under a dir
    foreach ($k in @($local_tree.Keys | sort -Descending)) {
        $skipped_message = get_nested_hash $local_tree @($k,'skip')
        if ($skipped_message) {
            $warns.Add("skipped $k`: $skipped_message")
            continue
        }

        $remote_size = get_nested_hash $remote_tree @($k,'size')
        $remote_type = get_nested_hash $remote_tree @($k,'type')
        $remote_test = get_nested_hash $remote_tree @($k,'test')
        $remote_mtime = get_nested_hash $remote_tree @($k,'mtime')
        $remote_mode = get_nested_hash $remote_tree @($k,'mode')

        $local_size = get_nested_hash $local_tree @($k,'size')
        $local_type = get_nested_hash $local_tree @($k,'type')
        $local_test = get_nested_hash $local_tree @($k,'test')
        $local_mtime = get_nested_hash $local_tree @($k,'mtime')
        $local_mode = get_nested_hash $local_tree @($k,'mode')

        if ($local_type -eq 'link') {
            # windows cannot handle link without admin access. so we don't touch links
            $cannot_by_file[$k] = 'link'
        }

        if (!$remote_tree[$k] -or $remote_type -ne $local_type) {
            #  remote missing this file or remote is a different type of file: eg, file vs directory
            if ($local_size) {
                if ($maxsize -ge 0 -and $RequiredSpace + $local_size -gt $maxsize) {
                    Write-Host "$(get_timestamp) size cutoff before $k`: RequiredSpace+local_size($RequiredSpace+$local_size) > maxsize($maxsize)"
                    break
                }
                $RequiredSpace += $local_size
            }

            if ($remote_tree[$k]) {
                # if remote file exists, remove it as it is different type
                $deletes.Add($k)
                $change_by_file[$k] = "newType"
            } else {
                $change_by_file[$k] = "add"
            }

            if ($local_type -eq 'dir') {
                # We don't tar dir because that would tar up all files under dir.
                # But the problem with this approach is that the dir mode
                # (permission) is then not recorded in the tar file. We will have
                # to keep and send the mode information separately (from the tar file).
                # so is mtime
                if ($check_mode) {
                    $modes.Add($k)
                }
                $need_mtime_reset[$k] = $true
            }
            continue
        }

        # at this point, both sides are same kind type: file, dir, or link
        if ($check_mode -and $local_type -ne 'link' -and $remote_mode -ne $local_mode) {
            $modes.Add($k)
        }

        # note: dir and link's sizes are hard-coded, so they will always equal.
        # therefore, we are really only compares file's sizes.
        # that is, only files can have different sizes.

        if ($remote_size -ne $local_size) {
            # only files can reach here
            if ($local_size) {
                if ($maxsize -ge 0 -and $RequiredSpace + $local_size -gt $maxsize) {
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

        if (!$local_test -and !$remote_test) {
            # if both missing tests, we compare mtime first
            # for fast check (default), if size and mtime match, then no need to update.
            # for deep check, or when mtime not matching (but size matching), resort to
            # cksum.

            if ($remote_mtime -ne $local_mtime) {
                $need_cksums.Add($k)
                $need_mtime_reset[$k] = $true
            } elseif ($deep_check -eq "1") {
                # $deep_check= "0" or $deep_check= "1"
                $need_cksums.Add($k)
            }
        } elseif (!$local_test -or !$remote_test) {
            # we reach here if only one test is missing.
            # note: if both tests are missing, the previous logic would have already taken care of it.
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
    send_text_line $myconn $need_cksums_string
    $writer.Flush()

    Write-Host "$(get_timestamp) collecting local cksums: $($need_cksums.count) items"
    $local_cksum_by_file = get_cksums $need_cksums $local_tree

    # unblock socket before reading
    $socket.Blocking = $false

    Write-Host "$(get_timestamp) waiting for remote cksums results"

    $patterns = @('<CKSUM_RESULTS>(.*)</CKSUM_RESULTS>')

    $captures = @(expect_socket $myconn $patterns @{ ExpectTimeout = $timeout })

    if (!$captures) {
        $reader.Dispose()
        $writer.Dispose()
        $stream.close()
        return
    }

    $remote_cksums_string = $captures[0][0]

    $remote_cksum_by_file = @{}
    if ($remote_cksums_string) {
        foreach ($row in ($remote_cksums_string -split "`n")) {
            if ($row -match '^(\d+) (.+)$') {
                $remote_cksum_by_file[$Matches[2]] = $Matches[1]
            }
        }
    }

    foreach ($f in $local_cksum_by_file.Keys) {
        if (!$remote_cksum_by_file[$f]) {
            Write-Host "ERROR: remote cksum results missing for $f"
            $change_by_file[$f] = "update"
        } elseif ($remote_cksum_by_file[$f] -ne $local_cksum_by_file[$f]) {
            $change_by_file[$f] = "update"
            $diff_by_file[$f] = $true # only type=file can get here.
        } elseif ($remote_tree[$f]['mtime'] -ne $local_tree[$f]['mtime']) {
            $need_mtime_reset[$f] = $true
        }
    }

    # test array merge: $a=1,2; $b=3,4; $a+$b
    foreach ($k in @($change_by_file.Keys + $deletes)) {
        # when we untar a file to overwrite an existing file, that file's parent dir timestamp get updated. 
        # therefore, we need to reset it.
        if ($k -match '^(.+)/') {
            $parent_dir = $Matches[1]
            if ($local_tree.ContainsKey($parent_dir)) {
                # # parent_dir may be filtered out by match/exclude patterns, therefore, we need to
                # check its existence
                $need_mtime_reset[$parent_dir] = $true
            }
        }
    }

    $mtimes = New-Object System.Collections.Generic.List[System.String]
    foreach ($f in $need_mtime_reset.Keys) {
        if ($local_tree[$f]) {
            $mtimes.Add($f)
        }
    }

    # don't unblock socket when writing; doing so would corrupt data.
    # instead, flush writes manually
    $socket.Blocking = $true

    foreach ($d in ($deletes | sort)) {
       "   delete $d"
    }

    $delete_string = "<DELETES>" + (($deletes | sort) -join "`n") + "</DELETES>"
    Write-Host "$(get_timestamp) sending deletes: $($deletes.Count) item(s)"
    send_text_line $myconn $delete_string

    $adds_files = New-Object System.Collections.Generic.List[System.String]
    $a = New-Object System.Collections.Generic.List[System.String]
    # align to the left:  "{0, -8}{1,-15}{2,-15}{3,-15}`n" -f "Locale", "Jar", "HelpSet", "Exception"
    # align to the right: "{0,8}{1,15}{2,15}{3,15}`n" -f "Locale", "Jar", "HelpSet", "Exception"

    foreach ($f in @($change_by_file.Keys | sort)) {
        $action = $change_by_file[$f]

        if ($cannot_by_file.ContainsKey($f)) {
            [string]$reason_for_cannot = $cannot_by_file[$f]
            "{0,6} {1} {2}" -f $action,$f,"skipped because of $reason_for_cannot"
        } else {
            $adds_files.Add($f)
            $a.Add(("{0,6} {1}" -f $action,$f))
            "{0,6} {1}" -f $action,$f
        }
    }

    # "test".TrimEnd("e") # this does nothing
    # "test".TrimEnd("t") # tes
    # $adds_string = $adds_string.TrimEnd("`n") # remove the last newline
    $adds_string = "<ADDS>" + ($a -join "`n") + "</ADDS>"
    Write-Host "$(get_timestamp) sending adds: $($adds_files.Count) item(s)"
    send_text_line $myconn $adds_string

    $a = @(
        foreach ($f in $mtimes) {
            $mt = $local_tree[$f]['mtime']
            "$mt $f"
        }
    )
    $mtime_string = "<MTIMES>" + ($a -join "`n") + "</MTIMES>"
    Write-Host "$(get_timestamp) sending mtimes: $($mtimes.Count) item(s)"
    send_text_line $myconn $mtime_string

    $a = @(
        if ($check_mode) {
            foreach ($f in $modes) {
                $mode = $local_tree[$f]['mode']
                $mode_string += "$mode $f"
            }
        }
    )
    $mode_string = "<MODES>" + ($a -join "`n") + "</MODES>`n"
    Write-Host "$(get_timestamp) sending modes: $($modes.Count) item(s)"
    send_text_line $myconn $mode_string

    $warn_string = "<WARNS>" + ($warns -join "`n") + "</WARNS>"
    Write-Host "$(get_timestamp) sending warns: $($warns.Count) item(s)"
    send_text_line $myconn $warn_string

    Write-Host "$(get_timestamp) sending required space: $RequiredSpace"
    send_text_line $myconn "<SPACE>$RequiredSpace</SPACE>"

    $writer.Flush() # flush data when writes are done.

    if (!$change_by_file) {
        Write-Host "$(get_timestamp) remote doesn't need to add/update any new files"
        return
    }

    # unblock socket when reading
    $socket.Blocking = $false

    Write-Host "$(get_timestamp) waiting for transfer mode from remote"

    $patterns = @('please send (data|diff|unpacked)')

    $captures = @(expect_socket $myconn $patterns @{ ExpectTimeout = $timeout })

    if (!$captures) {
        $reader.Dispose()
        $writer.Dispose()
        $stream.close()
        return
    }

    $mode = $captures[0][0]

    [string]$tmp_tar_file = $null
    try {
        # use [String] to prevent powershell automatically convert string to Path
        $tmp_tar_file = [string](get_tmp_name $tmpdir $prog @{ chkSpace = ($RequiredSpace * 2) })
    } catch {
        send_text_line $myconn $_.Exception.Message
        $writer.Flush()
        return;
    }

    Write-Host "$(get_timestamp) received tranfer mode: $mode. creating tmp local tar file: $tmp_tar_file"

    $files_to_tar = @()

    if ($mode -eq "diff") {
        $files_to_tar = ($diff_by_file.Keys | sort)
    } else {
        $files_to_tar = $adds_files
    }

    if (!$files_to_tar) {
        Write-Host "$(get_timestamp) no need to send anything to remote"
        return;
    }

    $files_by_front = @{}

    foreach ($f in $files_to_tar) {
        if ($local_tree[$f]['type'] -eq 'dir' -and !$local_tree[$f]['DirEmpty']) {
            # Skip non-empty dir because tar'ing dir will also tar the files underneath.
            # But we include empty dir
            Write-Verbose "Skipped dir $f because we will add files under it anyway"
            continue
        }

        $front = $local_tree[$f]['front']
        set_hash_of_arrays $files_by_front $front $f
    }

    $need_to_create_tar = $true
    $tar_created = $false

    if ($sevenZip -or $tptar) {
        # 7Zip and TpTar cannot take a list of files as input, therefore, we have to 
        # build a staging dir for them
        [string]$tmp_tar_dir = $null
        try {
            # use [String] to prevent powershell automatically convert string to Path
            $tmp_tar_dir = [string]((get_tmp_name $tmpdir $prog @{ chkSpace = ($RequiredSpace * 3) }) + "_dir")
        } catch {
            send_text_line $myconn $_.Exception.Message
            $writer.Flush()
            return;
        }

        [string]$old_tar_dir = $pwd
        foreach ($front in @($files_by_front.Keys | sort)) {
            cd $old_tar_dir # restore path from last loop

            cd $front

            foreach ($f in @($files_by_front[$front] | sort)) {
                # 1. copy one entry at a time, no recursive. Therefore, it is a dir
                # we only mkdir, not copy anything under it.
                # 2. we can only copy relative path
                if (!(copy_file_structure $f $tmp_tar_dir)) {
                    Write-Host "failed to copy $f $tmp_tar_dir, pwd=$pwd"
                    continue
                }
                $tar_created = $true
            }
        }
        cd $old_tar_dir # restore path from last loop

        [String]$cmd = $null
        if ($sevenZip) {
            $cmd = "Compress-7Zip $tmp_tar_file $tmp_tar_dir -Format Tar"
        } else {
            $cmd = "cd $tmp_tar_dir; TpTar -c -v -f $tmp_tar_file ."
        }
  
        Write-Verbose $cmd
        Invoke-Expression $cmd
        if (!$?) {
            Write-Host "cmd failed: $cmd"
        }
        cd $old_tar_dir # restore path
    } else {
        foreach ($front in @($files_by_front.Keys | sort)) {
            $files = @($files_by_front[$front] | sort)
            tar_file_list $front $tmp_tar_file $files $need_to_create_tar
            $need_to_create_tar = $false
            $tar_created = $true
        }
    }

    if (!$tar_created) {
        Write-Host "$(get_timestamp) no tar created, close this remote connection";
        return
    }

    # don't unblock socket when writing; doing so would corrupt data.
    # instead, flush writes manually
    $socket.Blocking = $true

    Write-Host "$(get_timestamp) sending tar-format data (mode=$mode) to remote."

    $in_stream = [System.IO.File]::OpenRead($tmp_tar_file)

    $tar_size = 0
    while ($size = $in_stream.Read($buffer,0,$BufferSize)) {
        # $writer.Write($buffer, 0, $size)
        #$encoded = xor_encode $buffer 'out' $size
        $encoded = $myconn.out_coder.xor($buffer,$size)
        $writer.Write($encoded,0,$size)
        $tar_size += $size
    }

    $in_stream.close()
    $socket.close()

    Write-Host "$(get_timestamp) sent tar_size=$tar_size. closed remote connection"

    if ($KeepTmpFile) {
        Write-Host "$(get_timestamp) tmp file $tmp_tar_file is kept"
    } else {
        Remove-Item $tmp_tar_file
    }
}


function copy_file_structure {
    # 1. copy one entry at a time, no recursive. Therefore, it is a dir
    # we only mkdir, not copy anything under it.
    # 2. we can only copy relative path   
    param(
        [string]$relative = $null,
        [Parameter(Mandatory = $true,position = 0)] [string]$src,
        [Parameter(Mandatory = $true,position = 1)] [string]$dst,
        [hashtable]$opt = $null
    )

    Write-Verbose "pwd=$pwd, cp src=$src, dst=$dst"
    #Set-PsDebug -Trace 1

    $old_pwd = $null
    if ($relative) {
        $old_pwd = $pwd
        cd $relative
        if (!$?) { exit 1 }
    }

    # trim the ending \
    $src = $src.TrimEnd('\')
    $dst = $dst.TrimEnd('\')

    if (!(Test-Path -Path $src)) {
        if ($old_pwd) { cd $old_pwd }
        return $false
    }

    if (!(Test-Path -Path $dst -ErrorAction SilentlyContinue)) {
        mkdir $dst
        if (!$?) {
            if ($old_pwd) { cd $old_pwd }
            return $false
        }
    } elseif (!(Test-Path -Path $dst -PathType Container)) {
        Write-Host "ERROR: dstr=$dst is not a directory"
        if ($old_pwd) { cd $old_pwd }
        return $false
    }

    $rellength = $pwd.ToString().Length

    # we are called one item a time, don't do -Recurse
    #@(Get-Item $src; Get-ChildItem $src -Recurse) | foreach {
    @(Get-Item $src) | ForEach-Object {
        # Write-Verbose "checking $($_.FullName)"
        $preserved = $_.FullName.SubString($rellength)
        $dstfull = "$dst\$preserved"

        if ($_.Attributes -eq 'Directory') {
            # we need this to copy empty dir
            New-Item -ItemType Directory -Path $dstfull -Force
        } else {
            # only pick plain file; link should already be filtered out in upstream
            New-Item -ItemType File -Path $dstfull -Force
            if (!$?) {
                Write-Host "ERROR: cmd failed: New-Item -ItemType File -Path $dstfull -Force. skipped"
                return $false
            }
            Copy-Item $_.FullName -Destination $dstfull
            if (!$?) {
                # remove the failed file. otherwise, this file would got into the tar file and we would
                # get this error when extracting tar: 
                #    Expand-7Zip : startIndex cannot be larger than length of string.
                Write-Host "ERROR: cmd failed: Copy-Item $_.FullName -destination $dstfull. Removed $dstfull"
                Remove-Item $dstfull -Force
                return $falase
            }
            # Write-Verbose("Copy-Item {0} -destination $dstfull" -f $_.FullName)
        }
    }
    if ($old_pwd) { cd $old_pwd }
    #Set-PsDebug -Trace 0
    return $true
}

function build_dir_tree {
    param(
        [Parameter(Mandatory = $true)][AllowEmptyCollection()] [string []]$paths = $null,
        [hashtable]$opt = $null
    )

    $AllowDenyPatterns = @{}
    if ($opt["AllowDenyPatterns"]) {
        $AllowDenyPatterns = $opt["AllowDenyPatterns"]
    }

    $saved_cwd = $pwd # save pwd as we keep changing dir later
    $tree = @{}

    foreach ($path in $paths) {
        cd $saved_cwd # start from the saved pwd

        if ($opt["RelativeBase"] -and !($path -match $abs_pattern)) {
            # RelativeBase is from command line and only on the to-pull side.
            Write-Verbose "cd $($opt["RelativeBase"])"

            # in powershell, try{}catch{} only catches terminating errors. 
            # 'cd' will not cause terminating error. therefore, we cannot use
            # try/catch. instead, we use $? which is $true/$false, not 0/1
            cd $opt["RelativeBase"]
            if (!$?) {
                # if there is an error, we just print locally, not to send to remote side.
                # therefore, we won't add the error into $tree.
                Write-Host "$(get_timestampe) cd $($opt["RelativeBase"]) failed. $path is skipped"
                continue
            }
        }

        $globs = @(Resolve-Path -Path $path | Select-Object -ExpandProperty "Path")

        if (!$?) {
            $message = "dir $path failed. skipped $path"
            Write-Host "$(get_timestamp) $message"
            set_nested_hash $tree @($path,"skip") $message
            continue
        }

        Write-Host "$(get_timestamp) resolved globs if any: $path => $(ConvertTo-Json $globs)"

        foreach ($p in $globs) {
            $abs_path = $null
            if (($p -match $abs_pattern)) {
                # examples: C://users, C:\\users, //netappsrv/data, \\netappsrv\data

                # this is abs path, still simplify it: a/../b -> b
                $abs_path = get_abs_path ($p)
            } else {
                if ($opt["RelativeBase"]) {
                    $abs_path = get_abs_path ("$($opt["RelativeBase"])/$p").Replace('\','/');
                } else {
                    $abs_path = get_abs_path ("$saved_cwd/$p").Replace('\','/');
                }
            }

            if (!$abs_path) {
                $message = "cannot find abs_path for $p"
                Write-Host "$(get_timestamp) $message"
                set_nested_hash $tree @($p,"skip") $message
                continue
            }

            if (!(Test-Path $abs_path) -and !(Get-ItemProperty $abs_path).LinkType) {
                # https://stackoverflow.com/questions/817794/find-out-whether-a-file-is-a-symbolic-link-in-powershell
                # to-do, not sure windows tar can handle broken symbolic links
                $message = "abs path $abs_path of $p not found"
                Write-Host "$(get_timestamp) $message"
                set_nested_hash $tree @($p,"skip") $message
                continue
            }

            if ($abs_path -match $root_dir_pattern) {
                $message = "cannot handle root dir: $p, abs=$abs_path"
                Write-Host "$(get_timestamp) $message"
                set_nested_hash $tree @($p,"skip") $message
                continue
            }

            # $back is the starting point to compare, a relative path
            # $front is the parent path (absolute path)
            # example:
            #    $0 client host port /a/b/*.csv /c/d/e f/g
            # $back will be *.csv and e.
            # when comparing *.csv, server needs to 'cd /a/b'. client needs to 'cd /f/g'.
            # when comparing e, server needs to 'cd /c/d'. client needs to 'cd /f/g'.

            $front = $null
            $back = $null

            # note: ` is escape for powershell, \ is escape for regex
            if ($abs_path -match '^(.*[/\\])(.+)') {
                $front,$back = $Matches[1],$Matches[2]
            } else {
                $message = "unexpected abs path format: $abs_path. expecting front/back"
                Write-Error $message
                set_nested_hash $tree @($p,"skip") $message
                continue
            }

            # now that we have clearly identified $back, we should use it as key rather than
            # $abs_path or $p as key
            if (!(is_allowed $abs_path $AllowDenyPatterns)) {
                set_nested_hash $tree @($back,"skip") "not allowed"
                continue
            }

            Write-Host "cd '$front'"
            cd $front
            if (!$?) {
                $message = "cd $front failed"
                Write-Error $message
                set_nested_hash $tree @($back,"skip") $message
                continue
            }

            $front_length = $front.Length

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
          foreach ($f in @(Get-ChildItem -Recurse tmp)) { write-host "$($f.Name) $($f.LastWriteTime)"}

          Get-ChildItem -Recurse tmp|resolve-path
         
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
            :FILES foreach ($item in @(Get-Item $back; Get-ChildItem -Recurse $back)) {
                $file_count++
                if ($file_count % 1000 -eq 0) {
                    Write-Host "$(get_timestamp) checked $file_count files"
                }

                $f = $item.FullName.SubString($front_length).Replace('\','/') # remote $front from full path

                if ($opt["matches2"] -and $opt["matches2"].Count -ne 0) {
                    $matched = $false
                    # $hash_of_array = @{ 'a'= @(1,2,3)}
                    # ConvertTo-Json $hash_of_array['a']
                    foreach ($p in $opt["matches2"]) {
                        if ($f -match $p) {
                            $matched = $true
                            break
                        }
                    }
                    if (!$matched) {
                        continue
                    }
                }

                if ($opt["excludes"] -and $opt["excludes"].Count -ne 0) {
                    foreach ($p in $opt["excludes"]) {
                        if ($f -match $p) {
                            continue FILES
                        }
                    }
                }

                if (!(is_allowed $f $AllowDenyPatterns)) {
                    set_nested_hash $tree @($f,"skip") "not allowed"
                    continue
                }

                if (!(Test-Path -LiteralPath $f -ErrorAction SilentlyContinue)) {
                    set_nested_hash $tree @($f,'skip') "no access"
                    continue
                }

                if (get_nested_hash $tree @($f,'back')) {
                    set_nested_hash $tree @($f,'skip') "duplicate target path: skip $front/$f"
                    continue
                } else {
                    set_nested_hash $tree @($f,'back') $back
                }
                set_nested_hash $tree @($f,'front') $front

                # $wintime = (Get-Item tmp\ps1\List-Exe.ps1).LastWriteTimeUtc
                $wintime = $item.LastWriteTimeUtc
                # UNIX style, total seconds from epoc. make sure both use UTC time
                # TotalSeconds is a double, with milliseconds behind the decimal point, and [int] may round it
                # up if it was greater than 0.5. What we need is to truncate
                # $mtime = [int]($wintime - $unixEpochStart).TotalSeconds
                $mtime = [math]::Truncate(($wintime - $unixEpochStart).TotalSeconds)

                set_nested_hash $tree @($f,'mtime') "$mtime" # save it as string because the remote_tree will come in as string too

                $type = $null
                $size = 0
                if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) {
                    # we cannot use $item.LinkType to check link because only link created by windows mklink
                    # command will set LinkType, cygwin "ln -s" will not set this. ReparsePoint is more reliable
                    $type = "link"
                    $size = 128 #hard coded
                    set_nested_hash $tree @($f,'test') $item.Target
                } elseif ($item.PSIsContainer) {
                    $type = "dir"
                    $size = 128 # hard coded 
                    set_nested_hash $tree @($f,'test') 'dir' # hard coded, means no test

                    # check whether the dir is empty, need this info when making a tar.
                    # if the directory is empty, we can tar the dir.
                    # if the directory is not empty, and if we don't want to tar all files
                    # in it, we can tar the dir.
                    if ((Get-ChildItem $f | Measure-Object).Count -eq 0) {
                        set_nested_hash $tree @($f,'DirEmpty') = $true
                    }
                } else {
                    # todo: there may be other unknown file types
                    $type = "file"
                    $size = $item.Length
                    # cksum is delayed because it is too time-consuming
                    # set_nested_hash $tree @($f, 'test') (cksum $f) 
                }
                set_nested_hash $tree @($f,'size') $size
                set_nested_hash $tree @($f,'type') $type

                $mode = $item.Mode # windows mode "darhsl" vs unix mode "drwxrwxrwx"
                set_nested_hash $tree @($f,'mode') $mode
                #ConvertTo-Json $tree     
            }
            Write-Host "$(get_timestamp) checked $file_count files in total"
        }
    }

    cd $saved_cwd

    return $tree
}

function diff_f1_f2 {
    param(
        [Parameter(Mandatory = $true)] [string]$f1 = $null,
        [Parameter(Mandatory = $true)] [string]$f2 = $null,
        [hashtable]$opt = $null
    )

    Compare-Object (Get-Content $f1) (Get-Content $f2)
}

function tar_file_list {
    param(
        [Parameter(Mandatory = $true)] [string]$front = $null,
        [Parameter(Mandatory = $true)] [string]$tar = $null,
        [Parameter(Mandatory = $true)] [string []]$files = $null,
        [Parameter(Mandatory = $true)] [boolean]$need_to_create_tar = $true,
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
    $file_string = @(foreach ($f in $files) { "'$f'" }) -join " "
    $substring = $file_string
    if ($file_string.Length -gt 50) {
        $substring = "$($file_string.Substring(0,50)) ...($($files.Count) items)"
    }

    Write-Host "$(get_timestamp) cd $front; tar -cf $tar $substring"

    $saved_tar_pwd = $pwd
    cd $front

    $command = $null
    if ($need_to_create_tar) {
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
    #Set-PsDebug -Trace 1
    Invoke-Expression $command | Out-Host
    #Set-PsDebug -Trace 0

    cd $saved_tar_pwd
}

function set_hash_of_arrays {
    param(
        [Parameter(Mandatory = $true)] [hashtable]$hash = $null,
        [Parameter(Mandatory = $true)] [string]$key = $null,
        [Parameter(Mandatory = $true)] $value = $null,
        $opt = $null
    )

    # we need a self-initialized hash of arrays. therefore, we implement this function
    # https://powershell.org/forums/topic/working-with-hash-of-arrays/

    if (!$hash[$key]) {
        $hash[$key] = New-Object System.Collections.Generic.List[System.String]
    }
    $hash[$key].Add($value)
}

<#
   $test_hash = @{}
   set_hash_of_arrays $test_hash "test_key" "test_value_1"
   set_hash_of_arrays $test_hash "test_key" "test_value_2"
   ConvertTo-Json $test_hash

   $array = New-Object System.Collections.Generic.List[System.String]
   # the following flat the array $test_hash["test_key"] into string
   $array.Add($test_hash["test_key"])
   $array.Add($test_hash["test_key"])
   ConvertTo-Json $array
#>

function set_nested_hash {
    param(
        [Parameter(Mandatory = $true)] [hashtable]$hash = $null,
        [Parameter(Mandatory = $true)] [string[]]$keys = $null,
        [Parameter(Mandatory = $true)] $value = $null,
        $opt = $null
    )
    # we need a self-initialized hash of arrays. therefore, we implement this function
    # https://powershell.org/forums/topic/working-with-hash-of-arrays/
    $count = $keys.Count
    $chop1 = $count - 2
    foreach ($key in $keys[0..$chop1]) {
        if (!$hash[$key]) {
            $hash[$key] = @{}
        }
        $hash = $hash[$key]
    }
    $hash[$keys[-1]] = $value
}

function get_nested_hash {
    param(
        [Parameter(Mandatory = $true)] [hashtable]$hash = $null,
        [Parameter(Mandatory = $true)] [string []]$keys = $null,
        $opt = $null
    )

    $count = $keys.Count
    $chop1 = $count - 2
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
    param(
        [Parameter(Mandatory = $true)] [MyConn]$myconn = $null,
        [Parameter(Mandatory = $true)] [string []]$patterns = $null,
        $opt = $null
    )

    $stream = $myconn.stream
    $reader = $myconn.reader
    $writer = $myconn.writer
    $socket = $myconn.socket
    $tcpclient = $myconn.tcpclient

    $data_str = ""
    $num_patterns = $patterns.Count
    $matched = New-Object boolean[] $num_patterns
    $captures = New-Object object[] $num_patterns
    $total_wait = 0
    $this_section_recv = 0;

    while ($tcpclient.Connected) {
        while ($stream.DataAvailable) {
            $size = $stream.Read($buffer,0,$BufferSize)

            if ($size -gt 0) {
                $this_section_recv += $size
                $myconn.in_count += $size
                Write-Verbose "received $size byte(s), total=$($myconn.in_count). this section so far $this_section_recv byte(s)"
                #$text = $encoding.GetString($buffer, 0, $size)
                #$decoded = xor_encode $buffer 'in' $size
                $decoded = $myconn.in_coder.xor($buffer,$size)
                $text = $encoding.GetString($decoded,0,$size)
                $data_str += $text
                Write-Verbose "data_str=$data_str"

                $all_matched = $true

                for ($i = 0; $i -lt $num_patterns; $i++) {
                    if ($matched[$i]) {
                        continue;
                    }
                    # Set-PsDebug -Trace 2
                    # multiline regex use "(?s)"
                    if ($data_str -match "(?s)$($patterns[$i])") {
                        $matched[$i] = $true
                        $captures[$i] = @($Matches[1],$Matches[2],$Matches[3]) # Matches[0] is the whole string
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
        if (($tcpclient.Client.Poll(1,[System.Net.Sockets.SelectMode]::SelectRead) -and
                $tcpclient.Client.Available -eq 0)) {
            $last_words = ""
            if ($data_str -ne "") {
                $tail_size = 100
                if ($data_str.Length -le $tail_size) {
                    $last_words = $data_str
                } else {
                    $last_words = $data_str.SubString($data_str.Length - $tail_size + 1)
                }
            }
            Write-Host "remote side closed connection. Last words: $last_words"
            return $null
        }

        if ($opt["ExpectTimeout"]) {
            if ($total_wait -gt $opt['ExpectTimeout']) {
                $message = "timed out after $($opt['ExpectTimeout']) seconds. very likely wrong protocol. expecting $expected_peer_protocol.*"
                Write-Host $message
                #$encoded = xor_encode [system.Text.Encoding]::Default.GetBytes($message) 'out'
                $encoded = $myconn.out_coder.xor([System.Text.Encoding]::Default.GetBytes($message))
                $writer.Write($encoded)
                $writer.Flush();
                sleep 2; # give a little time so that remote can process this messsage

                for ($i = 0; $i -lt $num_patterns; $i++) {
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
        $total_wait++
    }
}

# https://stackoverflow.com/questions/3038337/powershell-resolve-path-that-might-not-exist
function get_abs_path {
    param(
        [Parameter(Mandatory = $true)] $path = $null,
        $opt = $null
    )

    $abs_path = Resolve-Path $path -ErrorAction SilentlyContinue `
         -ErrorVariable myerror
    if (-not ($abs_path)) {
        $abs_path = $myerror[0].TargetObject
    }

    return $abs_path.ToString().Replace('\','/');
}

<#
[uint64 []]$array2 = @('0xFFFFFFFF', '0x1')
[uint64 []]$array2 = '0xFFFFFFFF','0x1'
$array2.getType()
$array2[0].getType()
#>

[uint64 []]$crctab = @(
    '0x00000000',
    '0x04c11db7','0x09823b6e','0x0d4326d9','0x130476dc','0x17c56b6b',
    '0x1a864db2','0x1e475005','0x2608edb8','0x22c9f00f','0x2f8ad6d6',
    '0x2b4bcb61','0x350c9b64','0x31cd86d3','0x3c8ea00a','0x384fbdbd',
    '0x4c11db70','0x48d0c6c7','0x4593e01e','0x4152fda9','0x5f15adac',
    '0x5bd4b01b','0x569796c2','0x52568b75','0x6a1936c8','0x6ed82b7f',
    '0x639b0da6','0x675a1011','0x791d4014','0x7ddc5da3','0x709f7b7a',
    '0x745e66cd','0x9823b6e0','0x9ce2ab57','0x91a18d8e','0x95609039',
    '0x8b27c03c','0x8fe6dd8b','0x82a5fb52','0x8664e6e5','0xbe2b5b58',
    '0xbaea46ef','0xb7a96036','0xb3687d81','0xad2f2d84','0xa9ee3033',
    '0xa4ad16ea','0xa06c0b5d','0xd4326d90','0xd0f37027','0xddb056fe',
    '0xd9714b49','0xc7361b4c','0xc3f706fb','0xceb42022','0xca753d95',
    '0xf23a8028','0xf6fb9d9f','0xfbb8bb46','0xff79a6f1','0xe13ef6f4',
    '0xe5ffeb43','0xe8bccd9a','0xec7dd02d','0x34867077','0x30476dc0',
    '0x3d044b19','0x39c556ae','0x278206ab','0x23431b1c','0x2e003dc5',
    '0x2ac12072','0x128e9dcf','0x164f8078','0x1b0ca6a1','0x1fcdbb16',
    '0x018aeb13','0x054bf6a4','0x0808d07d','0x0cc9cdca','0x7897ab07',
    '0x7c56b6b0','0x71159069','0x75d48dde','0x6b93dddb','0x6f52c06c',
    '0x6211e6b5','0x66d0fb02','0x5e9f46bf','0x5a5e5b08','0x571d7dd1',
    '0x53dc6066','0x4d9b3063','0x495a2dd4','0x44190b0d','0x40d816ba',
    '0xaca5c697','0xa864db20','0xa527fdf9','0xa1e6e04e','0xbfa1b04b',
    '0xbb60adfc','0xb6238b25','0xb2e29692','0x8aad2b2f','0x8e6c3698',
    '0x832f1041','0x87ee0df6','0x99a95df3','0x9d684044','0x902b669d',
    '0x94ea7b2a','0xe0b41de7','0xe4750050','0xe9362689','0xedf73b3e',
    '0xf3b06b3b','0xf771768c','0xfa325055','0xfef34de2','0xc6bcf05f',
    '0xc27dede8','0xcf3ecb31','0xcbffd686','0xd5b88683','0xd1799b34',
    '0xdc3abded','0xd8fba05a','0x690ce0ee','0x6dcdfd59','0x608edb80',
    '0x644fc637','0x7a089632','0x7ec98b85','0x738aad5c','0x774bb0eb',
    '0x4f040d56','0x4bc510e1','0x46863638','0x42472b8f','0x5c007b8a',
    '0x58c1663d','0x558240e4','0x51435d53','0x251d3b9e','0x21dc2629',
    '0x2c9f00f0','0x285e1d47','0x36194d42','0x32d850f5','0x3f9b762c',
    '0x3b5a6b9b','0x0315d626','0x07d4cb91','0x0a97ed48','0x0e56f0ff',
    '0x1011a0fa','0x14d0bd4d','0x19939b94','0x1d528623','0xf12f560e',
    '0xf5ee4bb9','0xf8ad6d60','0xfc6c70d7','0xe22b20d2','0xe6ea3d65',
    '0xeba91bbc','0xef68060b','0xd727bbb6','0xd3e6a601','0xdea580d8',
    '0xda649d6f','0xc423cd6a','0xc0e2d0dd','0xcda1f604','0xc960ebb3',
    '0xbd3e8d7e','0xb9ff90c9','0xb4bcb610','0xb07daba7','0xae3afba2',
    '0xaafbe615','0xa7b8c0cc','0xa379dd7b','0x9b3660c6','0x9ff77d71',
    '0x92b45ba8','0x9675461f','0x8832161a','0x8cf30bad','0x81b02d74',
    '0x857130c3','0x5d8a9099','0x594b8d2e','0x5408abf7','0x50c9b640',
    '0x4e8ee645','0x4a4ffbf2','0x470cdd2b','0x43cdc09c','0x7b827d21',
    '0x7f436096','0x7200464f','0x76c15bf8','0x68860bfd','0x6c47164a',
    '0x61043093','0x65c52d24','0x119b4be9','0x155a565e','0x18197087',
    '0x1cd86d30','0x029f3d35','0x065e2082','0x0b1d065b','0x0fdc1bec',
    '0x3793a651','0x3352bbe6','0x3e119d3f','0x3ad08088','0x2497d08d',
    '0x2056cd3a','0x2d15ebe3','0x29d4f654','0xc5a92679','0xc1683bce',
    '0xcc2b1d17','0xc8ea00a0','0xd6ad50a5','0xd26c4d12','0xdf2f6bcb',
    '0xdbee767c','0xe3a1cbc1','0xe760d676','0xea23f0af','0xeee2ed18',
    '0xf0a5bd1d','0xf464a0aa','0xf9278673','0xfde69bc4','0x89b8fd09',
    '0x8d79e0be','0x803ac667','0x84fbdbd0','0x9abc8bd5','0x9e7d9662',
    '0x933eb0bb','0x97ffad0c','0xafb010b1','0xab710d06','0xa6322bdf',
    '0xa2f33668','0xbcb4666d','0xb8757bda','0xb5365d03','0xb1f740b4'
)

$CksumBufferSize = 4 * 1024 * 1024
$CksumBuffer = New-Object System.Byte[] $CksumBufferSize
function cksum {
    param(
        [Parameter(Mandatory = $true)] [string]$file = $null,
        $opt = $null
    )

    [uint64]$cksum = 0
    $size = 0

    $ifd = $null
    try { $ifd = [System.IO.File]::OpenRead($file) } catch { Write-Host $_; exit 1 }

    #Set-PsDebug -Trace 1
    while ($n = $ifd.Read($CksumBuffer,0,$CksumBufferSize)) {
        $size += $n
        for ($i = 0; $i -lt $n; $i++) {
            $c = $CksumBuffer[$i]
            $index = (0xff -band ($cksum -shr 24)) -bxor $c
            $cksum = ([uint64]'0xffffffff' -band ($cksum -shl 8)) -bxor $crctab[$index]
            #Write-Host "c=$c, index=$index, cksum=$cksum"
        }
    }
    #Set-PsDebug -Trace 0
    $ifd.close()
    #Write-Host "size=$size, cksum=$cksum"
    # Extend with the length of the data
    while ($size -ne 0) {
        $c = $size -band 0xFF;
        $size = $size -shr 8;
        $cksum = ([uint64]'0xFFFFFFFF' -band ($cksum -shl 8)) -bxor $crctab[(0xFF -band ($cksum -shr 24)) -bxor $c];
        #Write-Host "size=$size, cksum=$cksum"
    }
    $cksum = (-bnot $cksum) -band [uint64]'0xffffffff'

    return $cksum
}
#cksum C:\Users\william\tmp\ps1\List-Exe.ps1
#foreach ($item in @(Get-ChildItem -Recurse C:\Users\william\tmp\ps1)) {cksum $item.FullName}

function get_cksums {
    param(
        [Parameter(Mandatory = $true)][AllowEmptyCollection()] [string []]$files = $null,
        [Parameter(Mandatory = $true)] [hashtable]$dir_tree = $null,
        $opt = $null
    )

    $cksum_by_file = @{}

    foreach ($f in $files) {
        $front = get_nested_hash $dir_tree @($f,'front')
        if (!$front) {
            Write-Host "ERROR: missing `$dir_tree['$f']['front']"
            continue
        }
        Write-Verbose "$(get_timestamp) calculating cksum('$front/$f')"
        $cksum_by_file[$f] = cksum "$front/$f"
    }

    return $cksum_by_file
}

function get_tmp_name {
    param(
        [Parameter(Mandatory = $true)] [string]$basedir,# "C:\Users\william\AppData\Local\Temp\",
        [Parameter(Mandatory = $true)] [string]$prefix,
        [hashtable]$opt = $null
    )

    $prefix = $prefix.Replace(".","_") # tpdist.ps1 -> tpdist_ps1

    #Set-PsDebug -Trace 1
    if ($opt['chkSpace']) {
        # assume tmp file is from C:
        $free_space = (Get-WmiObject win32_logicaldisk | Where-Object { $_.DeviceId -eq 'C:' }).FreeSpace
        if ($free_space -lt $opt['chkSpace']) {
            Write-Host "ERROR: FreeSpace ($free_space) <  Required space $($opt['chkSpace'])"
            throw "not enough free tmp space"
        } else {
            Write-Verbose "FreeSpace ($free_space) >= Required space $($opt['chkSpace'])"
        }
    }

    $yyyy,$mm,$dd,$HH,$MM,$ss = (Get-Date -Format "yyyy-MM-dd-HH-MM-ss").Split('-')

    # C:\Users\william\AppData\Local\Temp\tpsup
    $daydir = "$basedir/$yyyy$mm$dd"

    if (!(Test-Path -Path $daydir)) {
        mkdir $daydir | Out-Host # mkdir will return an object. if we don't take it, it will be returned to the calling function.
        if (!$?) { Write-Host "ERROR: mkdir $daydir failed"; exit 1 }

        # https://stackoverflow.com/questions/17829785/delete-files-older-than-15-days-using-powershell
        # remove daydir older than 7 days
        $cutoff = (Get-Date).AddDays(-7)
        Get-ChildItem -Path $basedir | Where-Object { $_.PSIsContainer -and $_.CreationTime -lt $cutoff } | Remove-Item -Force -Recurse
    }

    return [string]"$daydir/${prefix}_${HH}${MM}${ss}_$PID" # must add [string] otherwise powershell converts it to Path object.
}


if ($role.ToLower() -ne 'server' -and $role.ToLower() -ne 'client' -and $role.ToLower() -ne 'version') {
    usage ("Role must be either 'server' or 'client' or 'version'")
}

if ($role.ToLower() -eq "version") {
    Write-Host "version $version"
    exit 0
}

if (!$remainingArgs) {
    usage ("wrong number of args")
}

Write-Verbose "verbose=$v"
Write-Verbose "remainingArgs=$remainingArgs, size=$($remainingArgs.count)"

$user_specified = @{
    allowfile = $allowfile;
    denyfile = $denyfile;
    allowhost = $allowhost;
    denyhost = $denyhost;
}

$AccessMatrix = load_access $user_specified
Write-Verbose "AcccessMatrix = $(ConvertTo-Json $AccessMatrix)"

if ($role.ToLower() -eq 'server') {
    # this is server

    if (!$remainingArgs) {
        usage ("wrong numnber of args")
    }

    $local_dir = $null
    $remote_dirs = @()
    if (!$reverse) {
        # tpdist server port
        if ($remainingArgs.Count -ne 1) {
            usage ("wrong numnber of args")
        }
    } else {
        # tpdist -reverse server port remote_dir ... local_dir
        if ($remainingArgs.Count -lt 3) {
            usage ("wrong numnber of args")
        }

        $local_dir = $remainingArgs[-1]
        $remote_dirs = $remainingArgs[1..($remainingArgs.Count - 2)]
        Write-Verbose "remote_dirs=$remote_dirs, size=$($remote_dirs.count)"
        Write-Verbose "local_dir=$local_dir"

        if ((Test-Path -Path $local_dir) -and -not (Test-Path -Path $local_dir -PathType Container)) {
            Write-Host "ERROR: local_dir=$local_dir is not a directory"
            exit 1
        }
    }

    $listener_port = $remainingArgs[0]
    Write-Verbose "listener_port=$listener_port"

    while ($true) {
        $listener = New-Object System.Net.Sockets.TcpListener ([system.net.ipaddress]::any,$listener_port)

        if (-not $listener) {
            exit 1
        }

        $listener.Server.SetSocketOption("Socket","ReuseAddress",1)

        # this is big try-catch-finally is to make the above ReuseAddress to work
        # https://stackoverflow.com/questions/35322550/is-there-a-way-to-enable-the-so-reuseaddr-socket-option-when-using-system-net-ht
        try {
            $listener.start()
            Write-Verbose "listener = $(ConvertTo-Json($listener)))"
            Write-Host $(get_timestamp) "listener started at port $listener_port, max_idle=$maxidle seconds"

            $idle = 0
            [System.Net.Sockets.TcpClient]$tcpclient = $null;

            while ($true) {
                if ($listener.Pending()) {
                    $idle = 0 #reset idle timer

                    $tcpclient = $listener.AcceptTcpClient()
                    break;
                } else {
                    $idle += 1
                    if ($idle -gt $maxidle) {
                        Write-Host "$(get_timestamp) no new client connection for $maxidle seconds. Server quits"
                        $listener.Stop()
                        exit 0
                    }
                    sleep 1
                }
            }
        }
        catch { Write-Host $(get_timestamp) $_; exit 1 }
        finally { $listener.Stop() }

        # this command somehow will cause tcpclient disconnected.
        #Write-Verbose "tcpclient = $(ConvertTo-Json $tcpclient)"

        $peer_address = $tcpclient.Client.RemoteEndPoint.Address
        $peer_port = $tcpclient.Client.RemoteEndPoint.Port
        Write-Host "$(get_timestamp) accepted client $peer_address`:$peer_port."

        # https://docs.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_classes?view=powershell-7
        $myconn = [MyConn]::new($tcpclient,$encrypt_key)

        # [System.Net.Dns]::GetHostAddresses("127.0.0.1")
        # [System.Net.Dns]::GetHostAddresses("localhost")
        # [System.Net.Dns]::GetHostbyAddress("127.0.0.1") 
        # [system.net.dns]::GetHostEntry("127.0.0.1")
        # [system.net]::GetHostEntry("127.0.0.1")
        $all_hostnames = @()
        # https://docs.microsoft.com/en-us/dotnet/api/system.net.dns.gethostbyaddress?view=netframework-4.8
        # https://docs.microsoft.com/en-us/dotnet/api/system.net.iphostentry?view=netframework-4.8
        $dns_lookup = [System.Net.Dns]::GetHostByAddress($peer_address)
        $all_hostnames += $dns_lookup.HostName
        $all_hostnames += $dns_lookup.Aliases
        $all_hostnames += $peer_address
        if ($peer_address -eq "127.0.0.1") { $all_hostnames += "localhost" }
        Write-Host "$(get_timestamp) peer names: $all_hostnames"

        $allowed = $true
        foreach ($h in $all_hostnames) {
            if (!(is_allowed $h $AccessMatrix['host'])) {
                Write-Host "$(get_timestamp) $peer_address`: $h is not allowed to connect to us"
                send_text_line $myconn "$h is not allowed to connect to us"
                $allowed = $false
                break
            }
        }

        if ($allowed) {
            cd $old_pwd # restore pwd as it might be changed by last loop

            if (!$reverse) {
                #Write-Verbose "tcpclient = $(ConvertTo-Json $tcpclient)"          
                to_be_pulled $myconn
            } else {
                to_pull $myconn $remote_dirs $local_dir
            }
        }

        $tcpclient.close()

        cd $old_pwd # restore pwd

        Write-Host "`n----------------------------------------------------------------"
        Write-Host "$(get_timestamp) waiting for next client at port $listener_port, max_idle=$maxidle seconds"
    }
} else {
    # this is client

    if (!$remainingArgs) {
        usage ("wrong numnber of args")
    }

    $remote_dirs = @()
    $local_dir = $null

    if ($reverse) {
        if ($remainingArgs.Count -ne 2) {
            usage ("wrong numnber of args")
        }
    } else {
        if ($remainingArgs.Count -lt 4) {
            usage ("wrong numnber of args")
        }

        $local_dir = $remainingArgs[-1]
        $remote_dirs = $remainingArgs[2..($remainingArgs.Count - 2)]
        Write-Verbose "remote_dirs=$remote_dirs, size=$($remote_dirs.count)"
        Write-Verbose "local_dir=$local_dir"

        if ((Test-Path -Path $local_dir) -and -not (Test-Path -Path $local_dir -PathType Container)) {
            Write-Host "ERROR: local_dir=$local_dir is not a directory"
            exit 1
        }
    }

    $remote_host,$remote_port = $remainingArgs[0..1]
    Write-Verbose "remote_host=$remote_host"
    Write-Verbose "remote_port=$remote_port"

    [System.Net.Sockets.TcpClient]$tcpclient = $null
    try { $tcpclient = New-Object System.Net.Sockets.TcpClient ($remote_host,$remote_port) }
    catch { Write-Host $(get_timestamp) $_; exit 1 }

    $myconn = [MyConn]::new($tcpclient,$encrypt_key)

    Write-Verbose "connected server $($tcpclient.client.RemoteEndPoint.Address):$($tcpclient.client.RemoteEndPoint.Port)"

    if ($reverse) {
        to_be_pulled $myconn
    } else {
        to_pull $myconn $remote_dirs $local_dir
    }

    $tcpclient.close()

    Write-Host $(get_timestamp) "going back to old pwd: cd $old_pwd"

    #Set-Location -Path $old_pwd
    cd $old_pwd
}

exit 0
