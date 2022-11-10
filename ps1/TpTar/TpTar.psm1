
function usage {
    param([string]$prog = $null,[string]$message = $null)

    if ($message) {
        Write-Host $message
    }

    Write-Host "
Usage:

   $prog -x -v -f tar_test.tar
   $prog -c -v -f test.tar dir1 dir2
   $prog -t -v -f tar_test.tar
    
   -d      debug mode

Example:

   # Import the module
   PS> Import-Module   $cmd
   PS> Import-Module ./$cmd

   # Run the command from powershell
   PS> $cmd -d -t -v -f \\linux1\tian\junk.tar
   
   # Run the command from cmd prompt
   C:> powershell -ExecutionPolicy Bypass -NoLogo -NonInteractive -NoProfile -WindowStyle Hidden -Command `"Import-Module <module_path>\$cmd; TpTar -d -c -v -f \\linux1\tian\junk.tar`"

   # tar abs path should keep abs path
   PS> $cmd -d -c -v -f \\linux1\tian\junk.tar \Users\william\testdir
   C:\Users\william\testdir\
   C:\Users\william\testdir\a.txt
   C:\Users\william\testdir\dir_b\
   C:\Users\william\testdir\dir_b\c.txt

   # tar subfolder should keep subfolder
   PS> cd \Users\william\
   PS> $cmd -d -c -v -f \\linux1\tian\junk.tar testdir
   testdir\
   testdir\a.txt
   testdir\dir_b\
   testdir\dir_b\c.txt
   testdir\link_a.txt
   
   # tar current folder should start from items underneathk
   PS> cd \Users\william\testedir                                              
   PS> $cmd -d -c -v -f \\linux1\tian\junk.tar .
   .\
   .\a.txt
   .\dir_b\
   .\dir_b\c.txt                                                                        

"
    # don't exit as exit will kill the calling shell
    throw "check usage"
}

# only mimiced features of perl implementation of tar, Archive::Tar
# /usr/share/perl5/5.30/Archive/Tar.pm
# /usr/share/perl5/5.30/Archive/Tar/File.pm

# tar command source code
# https://github.com/Distrotech/tar/blob/distrotech-tar/src/list.c

# file command source code has a tar.h
# https://github.com/file/file/blob/master/src/tar.h

class TpTar{
    # https://www.sans.org/blog/powershell-byte-array-and-hex-functions/
    # in Powershell, Byte and System.Byte are the same.
    # this marks the end of tar file. It is an empty block.
    # As it has 512 bytes, hardcode doesn't look nice, therefore will init later
    #[Byte[]]$EndBlock = $0x0,0x0,.... repeat 512 times
    [Byte[]]$EndBlock = $null
    [string]$tarfile = 'Unknown'
    [int]$HeadSize = 512
    [int]$BlockSize = 512
    [int]$BufferSize = 10 * 1024 * 512

    # seconds from epoc to now, ie, mtime
    [datetime]$UnixEpochDateTime
    [System.TimeZoneInfo]$TZ
    # we cannot copy root dir
    # root dirs: /, //, C:, C:/, /cygdrive/c, /cygdrive/c/, or with \
    # note: ` is escape for powershell, \ is escape for regex
    [string]$root_dir_pattern = '^[a-zA-Z]:[\\/]*$|^[\\/]+$|^[\\/]+cygdrive[\\/]+|[\\/]+[\\/]*$';
    [string]$abs_pattern = '^[a-zA-Z]:[\\/]|^[\\/]+|^[\\/]+cygdrive[\\/]+|[\\/]+[\\/]';

    # https://powershellexplained.com/2016-11-06-powershell-hashtable-everything-you-wanted-to-know-about/
    # fancy hashtable
    static [hashtable]$template = @{
        Name = @{ octal = 0; size = 100 } # string
        Mode = @{ octal = 1; size = 8 }
        uid = @{ octal = 1; size = 8 }
        gid = @{ octal = 1; size = 8 }
        size = @{ octal = 0; size = 12 } # not *always* octal..
        mtime = @{ octal = 1; size = 12 }
        chksum = @{ octal = 1; size = 8 }
        type = @{ octal = 0; size = 1; } # character
        linkname = @{ octal = 0; size = 100 } # string
        magic = @{ octal = 0; size = 6 } # string
        version = @{ octal = 0; size = 2 } # 2 bytes
        uname = @{ octal = 0; size = 32 } # string                       
        gname = @{ octal = 0; size = 32 } # string                        
        devmajor = @{ octal = 1; size = 8 }
        devminor = @{ octal = 1; size = 8 }
        prefix = @{ octal = 0; size = 155 * 12 } # 155 x 12
    }
    # must in order, cannot skip
    static [String []]$handled_fields = @('name','mode','uid','gid','size','mtime','chksum','type','linkname','magic','version','uname','gname')

    TpTar ([string]$tarfile) {
        if ($tarfile -match $this.abs_pattern) {
            $this.tarfile = $tarfile
        } else {
            $this.tarfile = "$pwd\$tarfile"
            # PS C:\Users\william> cd \\linux1\tian
            # PS Microsoft.PowerShell.Core\FileSystem::\\linux1\tian> $pwd
            # Path
            # ----
            # Microsoft.PowerShell.Core\FileSystem::\\linux1\tian
            $this.tarfile = $this.tarfile -replace ("Microsoft.PowerShell.Core.FileSystem::", "")
        }

        Write-Verbose("tarfile = {0}" -f $this.tarfile)

        $this.EndBlock = New-Object System.Byte[] $this.BlockSize # tar end block is an empty block
        $this.UnixEpochDateTime = New-Object DateTime 1970,1,1,0,0,0,([DateTimeKind]::Utc)

        $strCurrentTimeZone = (Get-WmiObject win32_timezone).StandardName
        $this.TZ = [System.TimeZoneInfo]::FindSystemTimeZoneById($strCurrentTimeZone)
    }

    static print_exception ($e) {
        # https://stackoverflow.com/questions/38419325/catching-full-exception-message
        $formatstring = "{0} : {1}`n{2}`n" +
        "    + CategoryInfo          : {3}`n" +
        "    + FullyQualifiedErrorId : {4}`n"

        $fields = $e.InvocationInfo.MyCommand,
        $e.ErrorDetails,
        $e.InvocationInfo.PositionMessage,
        $e.CategoryInfo.ToString(),
        $e.FullyQualifiedErrorId

        Write-Host -ForegroundColor Red -BackgroundColor Black ($formatstring -f $fields)

        # [TpTar]::ResolveError($_)
    }

    static ResolveError ($ErrorRecord) {
       # tried stack trace, too wordy
       # https://stackoverflow.com/questions/795751/can-i-get-detailed-exception-stacktrace-in-powershell
       $ErrorRecord | Format-List * -Force |Out-Host
       $ErrorRecord.InvocationInfo |Format-List * | Out-Host
       $Exception = $ErrorRecord.Exception
       for ($i = 0; $Exception; $i++, ($Exception = $Exception.InnerException))
       {   "$i" * 80
           $Exception |Format-List * -Force | Out-Host
       }
    }

    [hashtable] read ([string]$action,[hashtable]$opt = $null) {
        [bool]$verbose = $opt.ContainsKey('verbose') -and $opt['verbose']
        [hashtable]$result = @{ error = 0; offset = 0 }
        [bigint]$previous_offset = 0

        $Buffer = New-Object System.Byte[] $this.BufferSize

        [string]$print_prefix = ""
        if ($action -eq 'extract') {
            $print_prefix = "extracting "
        } elseif ($action -eq 'go-to-end') {
            $print_prefix = "passed"
        }

        # we need to reset dir timestamp after extracted files under them.
        # therefore, we use this hashtable to save the information and use it later
        [hashtable]$mtimeDateTime_by_dir = @{}

        [System.IO.FileStream]$ifh = $null
        $ifh = [System.IO.File]::OpenRead($this.tarfile)
        # don't catch the error, let it boomb out
        <#
        try { $ifh = [System.IO.File]::OpenRead($this.tarfile) }
        catch {
            [TpTar]::print_exception($_)
            $result['error'] += 1
            return $result
        }
        #>

        [int]$skipped_blocks = 0
        [int]$skipped_from = 0
        #Set-PsDebug -Trace 1
        while ($n = $ifh.Read($Buffer,0,$this.HeadSize)) {
            Write-Verbose("read $n bytes at 0x{0:x}" -f $result['offset'])

            if ($n -ne $this.HeadSize) {
                Write-Host ("ERROR: cannot read enough bytes from the tarfile: imcomplete HEAD at offset=0x{0:x}" -f $result['offset'])
                $result['error'] += 1
                return $result
            }

            $BlockEndIndex = $this.HeadSize - 1
            if ([TpTar]::compare_array($Buffer[0..$BlockEndIndex],$this.EndBlock)) {
                if ($skipped_blocks) {
                    Write-Verbose ("skipped $skipped_blocks blocks from 0x{0:x}" -f $skipped_from)
                }
                # a empty ending block only means a previous tar ended here. doesn't mean an ending of the whole tar file
                Write-Verbose ("found previous tar's ending empty block at offset=0x{0:x}. skipped" -f $result['offset'])
                continue
            }

            Write-Verbose ("parsing head block at offset=0x{0:x}" -f $result['offset'])

            [hashtable]$entry = [TpTar]::parse_head($Buffer[0..$BlockEndIndex])
            Write-Verbose "entry = $(ConvertTo-Json($entry))"

            if ($entry -eq $null) {
                Write-Host ("ERROR: cannot parse HEAD block at offset=0x{0:x}" -f $result['offset'])
                $result['error'] += 1
                return $result
            }

            $previous_offset = $result['offset']
            $result['offset'] += $n

            if (!$entry) {
                if (!$skipped_blocks) {
                    # alert only once then just count the skipped blocks
                    Write-Host ("Error: Couldn't read HEAD block at offset=0x{0:x}. skipped" -f $previous_offset)
                    $result['error'] += 1
                    $skipped_from = $previous_offset
                }
                $skipped_blocks += 1

                # we don't return as we may find another block readable later
                continue
            } else {
                if ($skipped_blocks) {
                    # we have just skipped some blocks.
                    Write-Host ("skipped total $skipped_blocks blocks from 0x{0:x}. Find a readable block at offset=0x{1:x}" -f $skipped_from,$result['offset'])
                    $skipped_blocks = 0
                }
            }

            $entry_type = [TpTar]::get_type_desc($entry['type'])

            [datetime]$mtimeDateTime = $this.UnixEpochDateTime.AddSeconds($entry['mtime'])

            if ($verbose) {
                $mode1 = $null
                if ($entry_type -eq 'DIR') {
                    $mode1 = "d"
                } else {
                    $mode1 = "-"
                }

                $filename = $entry['name']
                if ($entry['linkname']) {
                    $filename += " -> "
                    $filename += $entry['linkname']
                }

                $mtimeLocal = [System.TimeZoneInfo]::ConvertTimeFromUtc($mtimeDateTime,$this.TZ)

                # drwxr-xr-x william/None      0 2020-07-16 08:18 testdir/
                # -rw-r--r-- william/None     15 2020-07-16 08:16 testdir/a.txt
                # drwxr-xr-x william/None      0 2020-07-16 08:18 testdir/dir_b/
                # -rw-r--r-- william/None     15 2020-07-16 08:18 testdir/dir_b/c.txt
                # lrwxrwxrwx william/None      0 2020-07-16 08:17 testdir/link_a.txt -> a.txt

                Write-Host ("$print_prefix{0,-1}{1,-4} {2,-15} {3,10} {4, -17} {5}" -f
                    $mode1,
                    #[Convert]::ToString($entry['mode'],8),
                    [TpTar]::get_string_from_mode($entry['mode']),
                    "$($entry['uname'])/$($entry['gname'])",
                    $entry['size'],$mtimeLocal.ToString("yyyy-MM-dd HH:mm"),
                    $filename
                )
            } else {
                Write-Host ("$print_prefix{0}" -f $entry['name'])
            }

            if ($entry_type -eq 'LABEL') {
                # skip labels
                Write-Verbose ("skipped LABEL block at offset=0x{0:x}" -f $previous_offset)
                continue
            }

            #if ($entry_type -eq 'FILE' -or $entry_type -eq 'LONGLINK') {
            if ($entry['size']) {
                # for any object with non-zero size             
                $file_size = $entry['size']
                $need_size = $this.compute_need_size($file_size)
                $attempt_size = $this.BufferSize
                $need_size_left = $need_size
                $file_size_left = $file_size

                Write-Verbose("file_size=0x{0:x}, need_size=0x{1:x}, next head block offset=0x{2:x}" -f 
                              $file_size,
                              $need_size,
                              $result['offset']+$need_size
                              )

                [string]$skip = $null
                if ($entry['name'] -eq 'pax_global_header' -or $entry['type'] -match '^(x|g)$') {
                    # skip PAX header
                    $skip = "PAX_HEAD"
                }

                if ($entry_type -ne 'FILE') {
                    # for non-zero sized object, I only know how to handle plain FILE
                    $skip = "$entry_type " + $entry['type']
                }

                [System.IO.FileStream]$out_stream = $null

                [string]$filename = $null
                if ($entry['name'] -match $this.abs_pattern) {
                    $filename = $entry['name']
                } else {
                    $filename = "$pwd\" + $entry['name']
                }

                if ($skip) {
                    Write-Host ("skip head block at 0x{0:x} and skip content at 0x{1:x}, size=0x{2:x} ({3}). reason: {4}" -f
                        $previous_offset,
                        $result['offset'],
                        $need_size,
                        $need_size,
                        $skip
                    )
                } elseif ($action -eq 'extract') {
                    # create an FileStream for output
                    Write-Verbose "write to $filename"

                    if ($filename -match '^(.+)/') {                     
                        $parent_dir = $Matches[1]
                        if (!(Test-Path -LiteralPath $parent_dir -PathType Container -ErrorAction SilentlyContinue )) {
                            Write-Verbose "mkdir -p $parent_dir"
                            New-Item -ItemType Directory -Path $parent_dir -Force
                            # powershell's "New-Item -ItemType Directory" does recursive mkdir automatically
                        }
                    }

                    $out_stream = [System.IO.File]::Create($filename)
                    # don't catch the error, let it boomb out
                    <#
                    try { $out_stream = [System.IO.File]::Create($filename) }
                    catch {[TpTar]::print_exception($_); $result['error'] += 1; return $result }
                    #>
                }

                while ($need_size_left -gt 0) {
                    if ($attempt_size -gt $need_size_left) {
                        $attempt_size = $need_size_left
                    }

                    $n2 = $ifh.Read($Buffer,0,$attempt_size)

                    if ($n2 -lt $attempt_size) {
                        Write-Host ("ERROR: read error on tarfile (missing data) at offset=0x{0:x}. Expected $attempt_size vs actual $n2 " -f $result['offset'])
                        $result['error'] += 1
                        return $result
                    }

                    if (!$skip -and $action -eq 'extract') {
                        if ($file_size_left -lt $attempt_size) {
                            # last block of data
                            $out_stream.Write($Buffer,0,$file_size_left)
                        } else {
                            $out_stream.Write($Buffer,0,$attempt_size)
                        }
                    }

                    $previous_offset = $result['offset']
                    $result['offset'] += $attempt_size

                    $need_size_left -= $attempt_size
                    $file_size_left -= $attempt_size
                }

                if ($out_stream) {
                    $out_stream.Flush()
                    $out_stream.Dispose()

                    # update file timestamp
                    Write-Verbose "set mtime on $filename"
                    (Get-Item -Path $filename).LastWriteTimeUtc = $mtimeDateTime
                }
            } elseif ($entry_type -eq 'DIR') {
                if ($action -eq 'extract') {

                    [string]$dir = $null

                    if ($entry['name'] -match $this.abs_pattern) {
                        $dir = $entry['name']
                    } else {
                        $dir = "$pwd\" + $entry['name']
                    }

                    if ($action -eq 'extract') {
                        if (Test-Path $dir) {
                            Write-Verbose "dir=$dir already exists"
                        } else {
                            Write-Verbose "mkdir -p $dir"
                            mkdir -p $dir
                        }
                    }

                    # will set mtime on dir after all files are extracted
                    $mtimeDateTime_by_dir[$dir] = $mtimeDateTime
                }
            } else {
                $result['error'] += 1
                Write-Host ("ERROR: cannot handle head block at offset=0x{0:x} type='{1}' desc='{2}' name='{3}', size=0x{4:x} ({5})" -f
                    $previous_offset,
                    $entry['type'],$entry_type,$entry['name'],
                    $entry['size'],
                    $entry['size']
                )
                if ($entry_type -eq 'SYMLINK') {
                    Write-Host ("ERROR: suggest to replace symlink with a copy. {0} -> {1}" -f $entry['name'],$entry['linkname'])
                }
            }
        }

        #Set-PsDebug -Trace 0
        $ifh.close()

        if ($action -eq 'extract') {
            foreach ($dir in @($mtimeDateTime_by_dir.Keys | sort)) {
                $mtimeDateTime = $mtimeDateTime_by_dir[$dir]
                Write-Verbose "set mtime on $dir"
                (Get-Item -Path $dir).LastWriteTimeUtc = $mtimeDateTime
            }
        }

        return $result
    }

    static [bool] compare_array ([byte[]]$a1,[byte[]]$a2) {
        # https://stackoverflow.com/questions/9598173/comparing-array-variables-in-powershell
        # $areEqual = @(Compare-Object $firstFolder $secondFolder -SyncWindow 0).Length -eq 0
        # This will return an array of differences between the two arrays or $null when the
        # arrays are equal. More precisely, the resulting array will contain an object for
        # each item that exists only in one array and not the other. The -SyncWindow 0 
        # argument will make the order in which the items appear in the arrays count as a
        # difference.
        $areEqual = @(Compare-Object $a1 $a2 -SyncWindow 0).Length -eq 0
        return $areEqual
    }

    static [string] get_string_from_mode ([int]$mode) {
        [string]$string = ""
        for ($i = 0; $i -lt 3; $i++) {
            [string]$sub_string = ""
            if ($mode -band 4) {
                $sub_string += "r"
            } else {
                $sub_string += "-"
            }

            if ($mode -band 2) {
                $sub_string += "w"
            } else {
                $sub_string += "-"
            }

            if ($mode -band 1) {
                $sub_string += "x"
            } else {
                $sub_string += "-"
            }

            $string = $sub_string + $string
            $mode = $mode -shr 3 # right shift 3 bits
        }

        return $string
    }

    static [object] parse_head ([Byte[]]$Buffer) {
        ### according to the posix spec, the last 12 bytes of the header are
        ### null bytes, to pad it to a 512 byte block. That means if these
        ### bytes are NOT null bytes, it's a corrupt header. See:
        ### www.koders.com/c/fidCE473AD3D9F835D690259D60AD5654591D91D5BA.aspx
        ### line 111
        [Byte[]]$HeadBlockEnd = 0x0,0x0,0x0,0x0,
        0x0,0x0,0x0,0x0,
        0x0,0x0,0x0,0x0

        if (![TpTar]::compare_array($Buffer[-12..-1],$HeadBlockEnd)) {
            Write-Host "Invalid head block. This block's ending 12 bytes should be empty \\0"
            return $null
        }

        # must in order, cannot skip

        [hashtable]$entry = @{}

        $relative_offset = 0
        foreach ($f in [TpTar]::handled_fields) {
            $size = [TpTar]::template[$f]['size']
            $octal = [TpTar]::template[$f]['octal']
            [string]$string = [System.Text.Encoding]::ASCII.GetString($Buffer,$relative_offset,$size)

            # this only trims the ending 0x0es. 
            #$string = $string.Trim([char]0) 

            # we want to chop everything starting from the first 0x0
            $index = $string.IndexOf([char]0);
            if ($index -ge 0) { $string = $string.Remove($index) }

            Write-Verbose "field=$f, rel_offset=$([String]::Format('0x{0:x}', $relative_offset)), size=$size, octal=$octal, string=$string, length=$($string.Length)"

            if ($f -eq 'name' -or $f -eq 'mode') {
                if (!$string) {
                    Write-Host "bad field='$f'"
                    return $null
                }
            }

            if ($string) {
                if ($f -eq 'size') {
                    # remove space. Windows Tar command sometimes put a space char after the number.
                    $index = $string.IndexOf([char]" ");
                    if ($index -ge 0) { $string = $string.Remove($index) }

                    # todo: should convert to bigint
                    $entry[$f] = [Convert]::ToInt64($string,8)
                } elseif ($octal) {
                    # remove space. Windows Tar command sometimes put a space char after the number.
                    $index = $string.IndexOf([char]" ");
                    if ($index -ge 0) { $string = $string.Remove($index) }

                    $entry[$f] = [Convert]::ToInt64($string,8)
                } else {
                    $entry[$f] = $string
                }
            } else {
                $entry[$f] = $string
            }

            $relative_offset += $size
        }

        [hashtable] $sum = [TpTar]::compute_head_block_chksum($Buffer[0..511])
        Write-Verbose "sum = $(ConvertTo-Json $sum)"
        $signed_sum = $sum['signed']
        $unsigned_sum = $sum['unsigned']

        if ($entry['chksum'] -eq $sum['signed']) {
            Write-Verbose("chksum=0{0} matched signed sum=0{1}" -f 
                            [Convert]::ToString($entry['chksum'],8), 
                            [Convert]::ToString($sum['signed'],8)
            )
        } elseif ($entry['chksum'] -eq $sum['unsigned']) {
            Write-Verbose("chksum=0{0} matched unsigned sum=0{1}" -f
                            [Convert]::ToString($entry['chksum'],8), 
                            [Convert]::ToString($sum['unsigned'],8)
            )
        } else {
            Write-Verbose("chksum=0{0} doesn't match either signed sum=0{1} or unsigned sum=0{2}" -f 
                           [Convert]::ToString($entry['chksum'],8),
                           [Convert]::ToString($sum['signed'],8),
                           [Convert]::ToString($sum['unsigned'],8)
                          )
            return $null
        }

        return $entry
    }

    static [string] get_type_desc ([string]$char) {
        [hashtable]$desc_by_char = @{
            "0" = "FILE"
            "1" = "HARDLINK"
            "2" = "SYMLINK"
            "3" = "CHARDEV"
            "4" = "BLOCKDEV"
            "5" = "DIR"
            "6" = "FIFO"
            "8" = "SOCKET"
            "9" = "UNKNOWN"
            "L" = "LONGLINK"
            "V" = "LABEL"
        }

        if ($desc_by_char.Contains($char)) {
            return $desc_by_char[$char]
        } else {
            return "UNKNOWN"
        }
    }

    static [string] get_type_char ([string]$desc) {
        [hashtable]$char_by_desc = @{
            "FILE" = "0"
            "HARDLINK" = "1"
            "SYMLINK" = "2"
            "CHARDEV" = "3"
            "BLOCKDEV" = "4"
            "DIR" = "5"
            "FIFO" = "6"
            "SOCKET" = "8"
            "UNKNOWN" = "9"
            "LONGLINK" = "L"
            "LABEL" = "V"
        }

        if ($char_by_desc.Contains($desc)) {
            return $char_by_desc[$desc]
        } else {
            return "UNKNOWN"
        }
    }

    [int64] compute_need_size ([int64]$size) {
        # force to round up
        [int64]$n = [int64][Math]::Ceiling($size / $this.BlockSize)
        return $n * $this.BlockSize
    }

    [hashtable] init_write_block ([string]$action) {
        [hashtable]$ret = @{
            error = 0
            ofh = $null
            offset = 0
        }

        [System.IO.FileStream]$ofh = $null
        if ($action -eq 'create') {
            Write-Verbose ("overwrite to {0}" -f $this.tarfile)
            $ofh = [System.IO.File]::Create($this.tarfile)
            # don't catch this error, let it bomb out
        } elseif ($action -eq 'append') {
            Write-Verbose "append to $this.tarfile"
            # we need to read till before the ending block\
            [hashtable]$result = $this.Read('go-to-end',@{})
            Write-Verbose ("found the end at 0x{0:x}" -f $result['offset'])
            $ret['offset'] = $result['offset']

            $ofh = [System.IO.File]::OpenWrite($this.tarfile)
            # don't catch this error, let it bomb out

            # https://docs.microsoft.com/en-us/dotnet/api/system.io.seekorigin?view=netcore-3.1
            # seek origin: 0 beginning, 1 current, 2 end.
            $expected_postion = $ret['offset']
            $actual_position = $ofh.Seek($expected_postion,0)

            if ($actual_position -ne $expected_postion) {
                throw ("failed to go to 0x{0:x}. we are at 0x{1:x}" -f $expected_postion,$actual_position)
            }
        } else {
            throw "unsupported action='$action'"
        }

        $ret['ofh'] = $ofh
        return $ret
    }

    # https://github.com/Distrotech/tar/blob/273975bec1ff7d591d7ab8a63c08a02a285ffad3/src/list.c
    static [string] get_abs_path ([string]$path) {
        # https://stackoverflow.com/questions/3038337/powershell-resolve-path-that-might-not-exist
        $myerror = $null
        $abs_path = Resolve-Path $path -ErrorAction SilentlyContinue -ErrorVariable myerror
        if (-not ($abs_path)) {
            $abs_path = $myerror[0].TargetObject
        }

        return $abs_path.ToString()
    }

    [int] write ([string]$action,[String []]$in_paths,[hashtable]$opt = $null) {
        [bool]$verbose = $opt.ContainsKey('verbose') -and $opt['verbose']
        [int]$error = 0

        Write-Verbose "in_paths = $(ConvertTo-Json($in_paths))"

        [Byte []]$Buffer = New-Object System.Byte[] $this.BufferSize
        [System.IO.FileStream]$ofh = $null

        [string]$saved_pwd = $pwd
        [int]$pwd_length = $saved_pwd.Length

        $file_count = 0
        foreach ($in_path in $in_paths) {
            [bool]$was_abs_path = $false
            if ($in_path -match $this.abs_pattern) {
                $was_abs_path = $true
            }

            [string]$in_abs_path = [TpTar]::get_abs_path($in_path)

            Write-Verbose "Recursively checking $in_path, abs path is $in_abs_path, saved_pwd=$saved_pwd, length=$pwd_length"

            [bool]$started_from_dot = $false # are we running tar -c -v -f junk.tar .

            foreach ($item in @(Get-Item $in_abs_path; Get-ChildItem -Recurse $in_abs_path)) {
                $file_count++
                if ($file_count % 1000 -eq 0) {
                    Write-Host "checked $file_count files"
                }

                $fullName = $item.FullName

                Write-Verbose "checking $fullName"

                if (!(Test-Path -LiteralPath $fullName -ErrorAction SilentlyContinue)) {
                    Write-Host "ERROR: $fullName no access. skipped"
                    continue
                }

                [hashtable]$prepared = @{
                    Mode = "0755"
                    uid = "1"
                    gid = "1"
                    chksum = "        " # must be 8 spaces because chksum calculator assumes chksum not set yet
                    linkname = ''
                    magic = 'ustar'
                    version = '00'
                    uname = 'dummy'
                    gname = 'dummy'
                }

                # replace \ with / to make the tar file portable to linux
                if ($was_abs_path) {
                    # if given full path, we use full path
                    $prepared['name'] = $item.FullName.Replace('\','/')
                } else {
                    # if given relative path, we use relative path
                    $prepared['name'] = $item.FullName.SubString($pwd_length).Replace('\','/'); # remove $front from fullname
                    if ($prepared['name'] -eq '') {
                        $prepared['name'] = './'
                        $started_from_dot = $true
                    } elseif ($prepared['name'] -match '^/') {
                        # this is not the abs path. it looks like an abs path now because we choped the front part, eg, /a/b -> /b
                        if ($started_from_dot) {
                            # /b -> ./b
                            $prepared['name'] = "." + $prepared['name']
                        } else {
                            # /b -> b
                            $prepared['name'] = $prepared['name'].SubString(1)
                        }
                    }
                }

                $name_length = $prepared['name'].Length
                if ($name_length > 100) {
                    Write-Host ("ERROR: name={0} length {1} is over 100. skipped. Suggest to use relative path or rename it shorter" -f $prepared['name'],$name_length)
                    continue
                }

                [string]$type = $null

                if ($item.LinkType) {
                    Write-Host "ERROR: $fullName is a link, we cannot handle it. skipped"
                    continue
                } elseif ($item.PSIsContainer) {
                    $type = "DIR"
                    $prepared['size'] = '0'
                } else {
                    # todo: there may be other unknown file types
                    $type = "FILE"
                    $prepared['size'] = [Convert]::ToString($item.Length,8)
                }

                $prepared['type'] = [TpTar]::get_type_char($type)

                $wintime = $item.LastWriteTimeUtc
                $mtime = [math]::Truncate(($wintime - $this.UnixEpochDateTime).TotalSeconds)
                $prepared['mtime'] = [Convert]::ToString($mtime,8) # need to convert number to a octal string

                # wipe out the first block in Buffer. we will build head block in buffer first.
                [System.Buffer]::BlockCopy($this.EndBlock,0,$Buffer,0,$this.HeadSize)

                $relative_offset = 0 # offset in head block
                foreach ($f in [TpTar]::handled_fields) {
                    $size = [TpTar]::template[$f]['size']
                    $octal = [TpTar]::template[$f]['octal']

                    if (-not $prepared.ContainsKey($f)) {
                        $prepared[$f] = ''
                    }

                    [string]$string = $null
                    if ($f -eq 'chksum') {
                        # hard copy the placeholder for chksum
                        $string = $prepared[$f]
                    } elseif ($octal -or $f -eq 'size') {
                        # octal numbers are padded with '0' on the left. Minus 1 is end the string with 0x0
                        $string = $prepared[$f].PadLeft($size - 1,'0')
                    } else {
                        # strings don't need padding
                        $string = $prepared[$f]
                    }

                    [byte []]$bytes = [System.Text.Encoding]::Default.GetBytes($string)
                    $length = $bytes.Count
                    if ($length -gt $size) {
                        throw ("$f={0} size $length is greater than limit $size" -f $prepared[$f])
                    }

                    Write-Verbose ("rel_offset=0x{0:x} field={1}, string={2}, length={3}, " -f $relative_offset,$f,$string,$length)
                    [System.Buffer]::BlockCopy($bytes,0,$Buffer,$relative_offset,$length)
                    $relative_offset += $size
                }

                # at last calculate chksum. this is to add all signed char of the head block, assuming
                # the chksum field were all filled with spaces before the calculation
                [hashtable]$sum = [TpTar]::compute_head_block_chksum($Buffer[0..511])
                Write-Verbose "sum = $(ConvertTo-Json($sum))"

                [int64]$chksum = $sum['sgined']                
                [int]$chksum_size = [TpTar]::template['chksum']['size']
                [string]$chksum_string = [Convert]::ToString($chksum,8).PadLeft($chksum_size - 1,'0')

                [byte []]$bytes = [System.Text.Encoding]::Default.GetBytes($chksum_string)
                $length = $bytes.Count
                Write-Verbose "rel_offset=0x94, chksum=$chksum, octal string=$chksum_string, length=$length"

                [System.Buffer]::BlockCopy($bytes,0,$Buffer,0x94,$length)
                [int]$chksum_end_index = 0x94 + $length
                $Buffer[$chksum_end_index] = 0x0

                # this set up the $this.out_fh and set the position
                # we delayed top open the file at the last moment, because once we open the tar file, we
                # could destroy the existing file.
                if (!$ofh) {
                    [hashtable]$result = $this.init_write_block($action)
                    $ofh = $result['ofh']
                }

                # record the head position so that we can roll back later
                # https://docs.microsoft.com/en-us/dotnet/api/system.io.seekorigin?view=netcore-3.1
                # seek origin: 0 beginning, 1 current, 2 end.        
                [int64]$saved_FileStream_postion = $ofh.Seek(0,1)

                Write-Verbose ("the above will write to head block at 0x{0:x}" -f $saved_FileStream_postion)

                # write the head block into the tar file
                $ofh.Write($Buffer,0,$this.HeadSize)

                if ($type -eq 'FILE') {
                    [System.IO.FileStream]$ifh = $null

                    try { $ifh = [System.IO.File]::OpenRead($fullname) }
                    catch {
                        [TpTar]::print_exception($_);
                        Write-Host "ERROR: cannot read $fullname. skipped";
                        Write-Verbose ("restored write position in FileStream to 0x{0:x}" -f $saved_FileStream_postion)
                        $ofh.Seek($saved_FileStream_postion,0)
                        $error += 1;
                        continue
                    }

                    Write-Verbose ("start writing data block(s) at 0x{0:x}" -f $ofh.Seek(0,1))
                    while ($n = $ifh.Read($Buffer,0,$this.BufferSize)) {
                        Write-Verbose "read and write $n bytes"
                        $ofh.Write($Buffer,0,$n)


                        [int]$extra = $n % $this.BlockSize;
                        if ($extra -ne 0) {
                            [int]$pad_size = $this.BlockSize - $extra
                            Write-Verbose "pad $pad_size 0x0 bytes"
                            # EndBlock are all 0x0 bytes
                            $n2 = $ofh.Write($this.EndBlock,0,$pad_size)
                        }
                    }
                }

                Write-Host $prepared['name']
            }
        }

        # end with two blank blocks
        [int64]$current_FileStream_postion = $ofh.Seek(0,1)
        Write-Verbose ("writing two ending blocks at 0x{0:x}" -f $current_FileStream_postion)
        $n3 = $ofh.Write($this.EndBlock,0,$this.HeadSize)
        $n3 = $ofh.Write($this.EndBlock,0,$this.HeadSize)
        $ofh.close()
        $ofh.Dispose()
        $ofh = $null

        return $error
    }

    static [hashtable] compute_head_block_chksum ([Byte []]$block) {
        [int64]$signed_sum = 0
        [int64]$unsigned_sum = 0

        [byte []]$chksum_placeholder = [System.Text.Encoding]::Default.GetBytes("        ") # 8 spaces

        $chksum_begin = 0x94
        $before_chksum_begin = $chksum_begin - 1

        foreach ($byte in @([Byte []]$block[0..$before_chksum_begin])) {
            $signed_sum += [sbyte]$byte
            $unsigned_sum += $byte
        }

        foreach ($byte in @([Byte []]$chksum_placeholder)) {
            $signed_sum += [sbyte]$byte
            $unsigned_sum += $byte
        }

        $after_chksum_end = 0x94 + 8

        foreach ($byte in @([Byte []]@($block[$after_chksum_end..511]))) {
            $signed_sum += [sbyte]$byte
            $unsigned_sum += $byte
        }

        $result = @{
            signed = $signed_sum
            unsigned = $unsigned_sum
        }

        return $result
    }
}

function TpTar {
    <#
  param (
      [Parameter(Mandatory = $true)][string]$front = $null,
      [Parameter(Mandatory = $true)][string]$tar = $null,
      [Parameter(Mandatory = $true)][string []]$files = $null,
      [Parameter(Mandatory = $true)][boolean]$need_to_create_tar = $true,
      [hashtable]$opt = $null
   )
[CmdletBinding(PositionalBinding=$false)]
#>
    param(
        [switch]$v = $false,# verbose 
        [switch]$x = $false,# extract a tar file
        [switch]$t = $false,# list table of contents
        [switch]$c = $false,# create a tar file
        [switch]$a = $false,# append a tar file
        [switch]$d = $false,# debug mode. $Debug is a revserved word; therefore we cannot use it.
        [Parameter(position = 0)] [string]$f = "unknown",
        [Parameter(ValueFromRemainingArguments = $true)] $remainingArgs = $null
    )

    [string]$cmd = $MyInvocation.MyCommand

    if ($f -eq 'unknown') {
        usage ($cmd,"wrong numnber of args")
    }

    Set-StrictMode -Version Latest
    #Set-PsDebug -Trace 1

    if ($d) {
        $verbosePreference = "Continue"
    }

    $version = "0.0"
    Write-Verbose "version = $version"

    Write-Verbose "pwd=$pwd, file=$f"

    $tar = [TpTar]::new($f)

    $opt = @{ verbose = $v }

    # https://stackoverflow.com/questions/58968118/how-to-return-non-zero-exit-code-from-a-powershell-module-function-without-closi
    # use throw to indicate failure. otherwise, successful.
    if ($t) {
        Write-Verbose "list table of contents from tar file"
        $result = $tar.Read('list',$opt)
    } elseif ($x) {
        Write-Verbose "extract from tar file"
        $tar.Read('extract',$opt)
    } elseif ($c) {
        Write-Verbose "create a tar file"
        if (!$remainingArgs) {
            usage ("wrong numnber of args")
        }
        $tar.Write('create',$remainingArgs,$opt)
    } elseif ($a) {
        Write-Verbose "append to a tar file"
        if (!$remainingArgs) {
            usage ("wrong numnber of args")
        }
        $tar.Write('append',$remainingArgs,$opt)
    } else {
        usage ("missing an action switch: a, c, l, x")
    }

    # don't run exit. this will exit the calling shell
    # exit 0
}

Export-ModuleMember -Function TpTar
