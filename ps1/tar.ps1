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

   MyTar([String]$file){
      $this._file = $file
      $this._buffer = new-object System.Byte[] $this._bufferSize
   }

   [object []]read() {
      $data = New-Object 'System.Collections.Generic.List[object]'
      $buffer = $this._buffer
      $buffersize = $this._bufferSize
      $HEAD = $this._HEAD
      $file = $this._file
 
      $handle = $null
      try { $handle = [System.IO.File]::OpenRead($file) } catch { Write-Host $_; exit 1 } 

      #Set-PsDebug -Trace 1
      while ( $n = $handle.Read($buffer, 0, $HEAD)) {
         Write-Verbose "read $n bytes"

         if ($n -ne $HEAD) {
            $this._error = "Cannot read enough bytes from the tarfile"
            return $null
         }

         [hashtable] $entry = $this.parse_chunk()
         exit 1

      }
   
      #Set-PsDebug -Trace 0
      $handle.close()
      
      return $data
   }

   [object] parse_chunk () {
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
         #$string = $string.Trim([char]0)
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

      Write-Verbose "entry = $(ConvertTo-Json($entry)))"

      return $entry
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