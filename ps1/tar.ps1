[CmdletBinding(PositionalBinding=$false)]param (
    [switch]$v = $false,
    [switch]$x = $extract,
    [switch]$t = $list,
    [switch]$c = $create,
    [Parameter(position=0)][string]$file = "unknown", 
    [Parameter(ValueFromRemainingArguments = $true)]$remainingArgs = $null
)

Set-StrictMode -Version Latest
#Set-PsDebug -Trace 1

if ($v) {
   $verbosePreference = "Continue"
}

$version = "0.0"
Write-Verbose "version = $version"

$HeadSize = 512   # tar head size
$BufferSize = 16*1024
$buffer = new-object System.Byte[] $BufferSize
$encoding = new-object System.Text.AsciiEncoding

$homedir = $HOME.Replace('\', '/');
Write-Verbose "homedir = $homedir"

# https://docs.microsoft.com/en-us/dotnet/api/system.io.path.gettemppath?view=netframework-4.8&tabs=windows
# C:\Users\UserName\AppData\Local\Temp\ 
$tmpdir = "$([System.IO.Path]::GetTempPath())\tpsup".Replace('\', '/');
Write-Verbose "tmpdir = $tmpdir"

$prog = ($PSCommandPath.Split('/\'))[-1]
Write-Verbose "prog = $prog"

$scriptdir = (Split-Path -Parent $PSCommandPath).Replace('\', '/');
Write-Verbose "scriptdir = $scriptdir"

# to get UNIX-style mtime, which seconds from epoc time.
# https://stackoverflow.com/questions/4192971/in-powershell-how-do-i-convert-datetime-to-unix-time
$unixEpochStart = new-object DateTime 1970,1,1,0,0,0,([DateTimeKind]::Utc)
# seconds from epoc to now, ie, mtime
# [int]([DateTime]::UtcNow - $unixEpochStart).TotalSeconds

# we cannot copy root dir
# root dirs: /, //, C:, C:/, /cygdrive/c, /cygdrive/c/, or with \
# note: ` is escape for powershell, \ is escape for regex
$root_dir_pattern = '^[a-zA-Z]:[\\/]*$|^[\\/]+$|^[\\/]+cygdrive[\\/]+[^\\/]+[\\/]*$';
$abs_pattern = '^[a-zA-Z]:[\\/]|^[\\/]+|^[\\/]+cygdrive[\\/]+[^\\/]+[\\/]';

$old_pwd = $pwd.ToString().Replace('\', '/');
Write-Verbose "saved_pwd=$old_pwd"

# https://www.sans.org/blog/powershell-byte-array-and-hex-functions/

function usage {
  param([string]$message = $null)

  if ($message) {
     Write-Host $message
  }

  Write-Host "
Usage:

   $prog -xvf tar_test.tar
   $prog -cvf test.tar dir1 dir2
   $prog -tvf tar_test.tar
    
"
   exit 1
}

# only mimiced features of perl implementation of tar, Archive::Tar
# /usr/share/perl5/5.30/Archive/Tar.pm
# /usr/share/perl5/5.30/Archive/Tar/File.pm

Class Tar {
   # https://www.sans.org/blog/powershell-byte-array-and-hex-functions/
   # in Powershell, Byte and System.Byte are the same.
   # this marks the end of tar file. It is an empty block.
   # As it has 512 bytes, hardcode doesn't look nice, therefore will init later
   #[Byte[]]$EndBlock = $0x0,0x0,.... repeat 512 times
   [Byte[]]$EndBlock = $null 
   [String]$file = 'Unknown'  
   [Byte[]]$Buffer= $null
   [Int] $HeadSize = 512
   [Int] $BlockSize = 512
   [Int] $BufferSize = 1024*512
   [bigInt] $offset = 0

   Tar([String]$file){
      $this.file = $file
      $this.Buffer = new-object System.Byte[] $this.BufferSize
      $this.EndBlock = new-object System.Byte[] $this.BlockSize    # tar end block is an empty block
   }

   [object []]read([String]$action) {     
      $handle = $null
      try { $handle = [System.IO.File]::OpenRead($this.file) } catch { Write-Host $_; return $null } 

      $this.offset = 0

      #Set-PsDebug -Trace 1
      while ( $n = $handle.Read($this.Buffer, 0, $this.HeadSize)) {
         Write-Verbose "read $n bytes"

         if ($n -ne $this.HeadSize) {
            Write-Host "Cannot read enough bytes from the tarfile: imcomplete HEAD at offset=$([String]::Format('0x{0:x}', $this.offset))"
            return $null
         } 

         $BlockEndIndex = $this.HeadSize-1
         if ([Tar]::compare_array($this.Buffer[0..$BlockEndIndex], $this.EndBlock)) {
            # a empty block means tar end
            Write-Verbose "hit ending empty block at offset=$([String]::Format('0x{0:x}', $this.offset))"
            break
         }       

         [hashtable] $entry = $this.parse_chunk()        
         Write-Verbose "entry = $(ConvertTo-Json($entry))"

         $this.offset += $n

         if (!$entry) {
            Write-Host "Couldn't read HEAD chunk at offset=$([String]::Format('0x{0:x}', $this.offset))"a
            continue
         }        

         $entry_type = $this.get_type_desc($entry['type'])

         $mode1=$null

         if ($entry_type -eq 'DIR' ) {
            $mode1="d"
         } else {
            $mode1="-"
         }

         Write-Host( "{0,-1}{1,-4}{2,-17}{3,-15}`n" -f $mode1, [Convert]::ToString($entry['mode'],8), 2, 1) #"$entry['uid']/$entry['gid']", 1





         if ($entry_type -eq 'LABEL') {
            # skip labels
            continue
         }

         if ($entry_type -eq 'FILE' -or $entry_type -eq 'LONGLINK') {
            $need_size = $this.compute_need_size($entry['size'])          
            
            [bool] $skip = 0
            if ( $entry['name'] -eq 'pax_global_header' -or $entry['type'] -match '^(x|g)$' ) {
               # skip PAX header
               $skip = 1
            }

            $attempt_size = $this.BufferSize
            $amount_left = $need_size
            while ($amount_left -gt 0) {
               if ($attempt_size -gt $amount_left) {
                   $attempt_size = $amount_left
               }

               $n2 = $handle.Read($this.Buffer, 0, $attempt_size)
               if ($n2 -lt $attempt_size) {
                  Write-Host "Read error on tarfile (missing data) at offset=$([String]::Format('0x{0:x}', $this.offset)). Expected $attempt_size vs actual $n2 "
                  return $null
               }

               $this.offset += $attempt_size
               $amount_left -= $attempt_size
            }                      
         }
      }
   
      #Set-PsDebug -Trace 0
      $handle.close()
      
      return $null
   }

   static [bool] compare_array([byte[]]$a1, [byte[]]$a2) {
      # https://stackoverflow.com/questions/9598173/comparing-array-variables-in-powershell
      # $areEqual = @(Compare-Object $firstFolder $secondFolder -SyncWindow 0).Length -eq 0
      # This will return an array of differences between the two arrays or $null when the
      # arrays are equal. More precisely, the resulting array will contain an object for
      # each item that exists only in one array and not the other. The -SyncWindow 0 
      # argument will make the order in which the items appear in the arrays count as a
      # difference.
      $areEqual =@(Compare-Object $a1 $a2 -SyncWindow 0).Length -eq 0
      return $areEqual
   }

   [object] parse_chunk () {
      ### according to the posix spec, the last 12 bytes of the header are
      ### null bytes, to pad it to a 512 byte block. That means if these
      ### bytes are NOT null bytes, it's a corrupt header. See:
      ### www.koders.com/c/fidCE473AD3D9F835D690259D60AD5654591D91D5BA.aspx
      ### line 111
      [Byte[]]$HeadBlockEnd = 0x0,0x0,0x0,0x0,
                              0x0,0x0,0x0,0x0,
                              0x0,0x0,0x0,0x0

      if (! [Tar]::compare_array($this.Buffer[-12..-1], $HeadBlockEnd)) {
         Write-Host  "Invalid head block starting at offset=$([String]::Format('0x{0:x}', $this.offset)). This block's ending 12 bytes should be empty \\0"
         return $null
      } 

      # https://powershellexplained.com/2016-11-06-powershell-hashtable-everything-you-wanted-to-know-about/
      # fancy hashtable

      [hashtable] $tmpl = @{
        name        = @{ octal=0; size=100} # string
        mode        = @{ octal=1; size=8  }
        uid         = @{ octal=1; size=8  }
        gid         = @{ octal=1; size=8  }
        size        = @{ octal=0; size=12 } # not *always* octal..
        mtime       = @{ octal=1; size=12 }
        chksum      = @{ octal=1; size=8  }
        type        = @{ octal=0; size=1; } # character
        linkname    = @{ octal=0; size=100} # string
        magic       = @{ octal=0; size=6  } # string
        version     = @{ octal=0; size=2  } # 2 bytes
        uname       = @{ octal=0; size=32 } # string                       
        gname       = @{ octal=0; size=32 } # string                        
        devmajor    = @{ octal=1; size=8  } 
        devminor    = @{ octal=1; size=8  }
        prefix      = @{ octal=0; size=155*12; numeric=0 } # 155 x 12
      }

      # must in order, cannot skip
      [String []] $handled_fields = @('name', 'mode', 'uid', 'gid','size', 'mtime', 'chksum', 'type', 'linkname')

      [hashtable] $entry = @{}

      $relative_offset = 0
      foreach ($f in $handled_fields) {
         $size = $tmpl[$f]['size']
         $octal = $tmpl[$f]['octal']
         [String] $string = [System.Text.Encoding]::ASCII.GetString($this.Buffer, $relative_offset, $size)

         # this only trims the ending 0x0es. 
         #$string = $string.Trim([char]0) 

         # we want to chop everything starting from the first 0x0
         $index = $string.IndexOf([char]0);
         if ($index -ge 0) { $string = $string.Remove($index) } 

         Write-Verbose "field=$f, rel_offset=$([String]::Format('0x{0:x}', $relative_offset)), size=$size, octal=$octal, string=$string, length=$($string.Length)"

         if ($f -eq 'size') {
            # todo: should convert to bigint
            $entry[$f] = [Convert]::ToInt64($string,8)
         } elseif ($octal) {
            #$string = "00000755"
            $entry[$f] = [Convert]::ToInt64($string, 8)
         } else {
            $entry[$f] = $string
         }     
         
         $relative_offset += $size   
      }

      return $entry
   }

   [string] get_type_desc ([string] $char) {
      [hashtable] $desc_by_char = @{
         "0"="FILE"
         "1"="HARDLINK"
         "2"="SYMLINK"
         "3"="CHARDEV"
         "4"="BLOCKDEV"
         "5"="DIR"
         "6"="FIFO"
         "8"="SOCKET"
         "9"="UNKNOWN"
         "L"="LONGLINK"
         "V"="LABEL"
      }

      if ($desc_by_char.Contains($char)) {
        return $desc_by_char[$char]
      } else {
        return "UNKNOWN"
      }
   }

   [string] get_type_char ([string] $desc) {
      [hashtable] $char_by_desc = @{
         "FILE"="0"
         "HARDLINK"="1"
         "SYMLINK"="2"
         "CHARDEV"="3"
         "BLOCKDEV"="4"
         "DIR"="5"
         "FIFO"="6"
         "SOCKET"="8"
         "UNKNOWN"="9"
         "LONGLINK"="L"
         "LABEL"="V"
      }

      if ($char_by_desc.Contains($desc)) {
        return $char_by_desc[$desc]
      } else {
        return "UNKNOWN"
      }
   }

   [Int64] compute_need_size ([Int64] $size) {
      [Int64] $n = $size/$this.BlockSize
      if ($size % $this.BlockSize) {
         $n += 1
      }
      return $n*$this.BlockSize
   }
}


if ($file -eq 'unknown') {
      usage("wrong numnber of args")
}

if ($file) {
   if ( ! ($file -match $abs_pattern) ) {
      $file="$pwd\$file"
   }
   Write-host "file=$file"
}
$tar = [Tar]::new($file)
$tar.read('list')

exit 0