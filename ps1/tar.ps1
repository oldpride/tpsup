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

#$AsciiEncoding = new-object System.Text.AsciiEncoding
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

# mimic perl implementation
# /usr/share/perl5/5.30/Archive/Tar.pm
# /usr/share/perl5/5.30/Archive/Tar/File.pm

Class MyTar {
   [Byte []]$_data = $null
   [String]$_error = ''
   [String]$_file = 'Unknown' 
   [Int] $_bufferSize = 4*1024*1024
   [System.Byte[]]$_buffer= $null
   [Int] $_HEAD = 512
   [Int] $_BLOCK = 512
   [System.Byte[]]$_endBlock = $null
   [System.Byte[]]$_headEnd = $null

   MyTar([String]$file){
      $this._file = $file
      $this._buffer = new-object System.Byte[] $this._bufferSize
      $this._endBlock = new-object System.Byte[] $this._HEAD    # tar end block is an empty block
      $this._headEnd = new-object System.Byte[] 12   # tar HEAD end block with 12 empty bytes
   }

   [object []]read() {
      # $data = New-Object 'System.Collections.Generic.List[object]'
      $data = @()
      $HEAD = $this._HEAD
 
      $handle = $null
      try { $handle = [System.IO.File]::OpenRead($this._file) } catch { Write-Host $_; exit 1 } 

      [bigInt] $offset = 0

      #Set-PsDebug -Trace 1
      while ( $n = $handle.Read($this._buffer, 0, $HEAD)) {
         Write-Verbose "read $n bytes"

         if ($n -ne $HEAD) {
            Write-Host "Cannot read enough bytes from the tarfile: imcomplete HEAD at offset=$([String]::Format('0x{0:x}', $offset))"
            return $null
         } 

         if ($this.compare_array($this._buffer[0..511], $this._endBlock)) {
            # a empty block means tar end
            Write-Verbose "hit ending empty block at offset=$([String]::Format('0x{0:x}', $offset))"
            break
         }       

         [hashtable] $entry = $this.parse_chunk()        
         Write-Verbose "entry = $(ConvertTo-Json($entry))"
         Write-Verbose "type = $($this.get_type($entry['type']))"

         if (!$entry) {
            Write-Host "Couldn't read HEAD chunk at offset=$([String]::Format('0x{0:x}', $offset))"
            next
         }

         $offset += $n

         $entry_type = $this.get_type($entry['type'])

         if ($entry_type -eq 'LABEL') {
            # skip labels
            continue
         }

         if ($entry_type -eq 'FILE' -or $entry_type -eq 'LONGLINK') {
            $block = $this.BLOCK_SIZE($entry['size'])          
            
            if ( $entry['name'] -eq 'pax_global_header' -or $entry['type'] -match '^(x|g)$' ) {
               # skip PAX header
               $this_block = 64 * 512
               $amt = $block
               while ($amt -gt 0) {
                  if ($this_block -gt $amt) {
                     $this_block = $amt
                  }

                  $n2 = $handle.Read($this._buffer, 0, $this_block)
                  if ($n2 -lt $this_block) {
                     Write-Host "Read error on tarfile (missing data) at offset=$([String]::Format('0x{0:x}', $offset)). Expected $this_block vs actual $n2 "
                     return $null
                  }

                  $offset += $this_block
                  $amt    -= $this_block
               }           
            } else {
               $this_block = 64 * 512
               $amt = $block
               while ($amt -gt 0) {
                  if ($this_block -gt $amt) {
                     $this_block = $amt
                  }

                  $n2 = $handle.Read($this._buffer, 0, $this_block)
                  if ($n2 -lt $this_block) {
                     Write-Host "Read error on tarfile (missing data) at offset=$([String]::Format('0x{0:x}', $offset)). Expected $this_block vs actual $n2 "
                     return $null
                  }

                  $offset += $this_block
                  $amt    -= $this_block
               }
            }
         }
      }
   
      #Set-PsDebug -Trace 0
      $handle.close()
      
      return $data
   }

   <#
   [bool]compare_array([object[]]$a1, [object[]]$a2) {
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
   #>

   [bool]compare_array([byte[]]$a1, [byte[]]$a2) {
      if ($a1.Length -ne $a2.Length ) {
         return $false
      }

      for ($i=0; $i -lt $a1.Length; $i++) {
         if ($a1[$i] -ne $a2[$i]) {
            return $false
         }
      }

      return $true
   }

   [object] parse_chunk () {

      ### according to the posix spec, the last 12 bytes of the header are
      ### null bytes, to pad it to a 512 byte block. That means if these
      ### bytes are NOT null bytes, it's a corrupt header. See:
      ### www.koders.com/c/fidCE473AD3D9F835D690259D60AD5654591D91D5BA.aspx
      ### line 111
      # todo: optimize the code

      if (! $this.compare_array($this._buffer[-12..-1], $this._headEnd)) {
         Write-Host  "Invalid header block, ending 12 bytes should be empty \\0"
         return $null
      } 

      # https://powershellexplained.com/2016-11-06-powershell-hashtable-everything-you-wanted-to-know-about/
      # fancy hashtable

      [hashtable] $tmpl = @{
        name        = @{ octal=0; size=100} # string
        mode        = @{ octal=1; size=8  }
        uid         = @{ octal=1; size=8  }
        gid         = @{ octal=1; size=8  }
        size        = @{ octal=0; size=12 } # cdrake - not *always* octal..
        mtime       = @{ octal=1; size=12 }
        chksum      = @{ octal=1; size=8  }
        type        = @{ octal=0; size=1; } # character
        linkname    = @{ octal=0; size=100} # string
        magic       = @{ octal=0; size=6  } # string
        version     = @{ octal=0; size=2  } # 2 bytes
        uname       = @{ octal=0; size=32 } # string                       
        gname       = @{ octal=0; size=32 } # string                        
        devmajor    = @{ octal=1; size=8             } 
        devminor    = @{ octal=1; size=8             }
        prefix      = @{ octal=0; size=155*12; numeric=0 } # 155 x 12
      }

      # must in order, cannot skip
      [String []] $handled_fields = @('name', 'mode', 'uid', 'gid','size', 'mtime', 'chksum', 'type', 'linkname')

      [hashtable] $entry = @{}

      $offset = 0
      foreach ($f in $handled_fields) {
         $size = $tmpl[$f]['size']
         $octal = $tmpl[$f]['octal']
         #$bytes = $this._buffer[$offset, $offset + $size]
         [String] $string = [System.Text.Encoding]::ASCII.GetString($this._buffer, $offset, $size)
         #$string = $string.Trim([char]0) # this only trims the ending zeros
         $index = $string.IndexOf([char]0);
         if ($index -ge 0) { $string = $string.Remove($index) }
         
         $length = $string.Length   

         Write-Verbose "field=$f, offset=$([String]::Format('0x{0:x}', $offset)), size=$size, octal=$octal, string=$string, length=$length"

         #continue
         if ($f -eq 'size') {
            # todo: should convert to bigint
            $entry[$f] = [Convert]::ToInt64($string,8)
         } elseif ($octal) {
            #$string = "00000755"
            $entry[$f] = [Convert]::ToInt64($string, 8)
         } else {
            $entry[$f] = $string
         }     
         
         $offset += $size   
      }

      return $entry
   }

   [string] get_type ([string] $char) {
      [hashtable] $type_by_char = @{
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

      if ($type_by_char.Contains($char)) {
        return $type_by_char[$char]
      } else {
        return "UNKNOWN"
      }
   }

   [string] get_typechar ([string] $type) {
      [hashtable] $char_by_type = @{
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

      if ($char_by_type.Contains($type)) {
        return $char_by_type[$type]
      } else {
        return "UNKNOWN"
      }
   }

   [Int64] BLOCK_SIZE ([Int64] $size) {
      [Int64] $n = $size/$this._BLOCK
      if ($size % $this._BLOCK) {
         $n += 1
      }

      return $n*$this._BLOCK
   }

}



if ($file -eq 'unknown') {
      usage("wrong numnber of args")
}

$abs_pattern = '^[a-zA-Z]:[\\/]|^[\\/]+|^[\\/]+cygdrive[\\/]+[^\\/]+[\\/]'

if ($file) {
   if ( ! ($file -match $abs_pattern) ) {
      $file="$pwd\$file"
   }
   Write-host "file=$file"
}
$tar = [MyTar]::new($file)
$tar.read()

exit 0