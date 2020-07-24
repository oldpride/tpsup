$env:Path = "C:\Program Files (x86)\Common Files\Oracle\Java\javapath;C:\Program Files\Python37\Scripts\;C:\Program Files\Python37\;C:\WINDOWS\system32;C:\WINDOWS;C:\WINDOWS\System32\Wbem;C:\WINDOWS\System32\WindowsPowerShell\v1.0\;C:\WINDOWS\System32\OpenSSH\;C:\src\flutter\bin;C:\Program Files\Git\cmd;C:\Program Files\Intel\WiFi\bin\;C:\Program Files\Common Files\Intel\WirelessCommon\;C:\Program Files\PuTTY\;C:\Users\william\AppData\Local\Microsoft\WindowsApps;C:\Users\william\AppData\Local\Android\Sdk\platform-tools;C:\Users\william\AppData\Local\Android\Sdk\emulator;;C:\Program Files\JetBrains\PyCharm Community Edition 2019.1.3\bin;C:\users\william\sitebase\github\tpsup\ps1"
#$env:Path



[Environment]::SetEnvironmentVariable("Path", $env:Path, "User")
#[Environment]::GetEnvironmentVariable("Path", "User")

# https://docs.microsoft.com/en-us/powershell/module/microsoft.powershell.core/add-pssnapin?view=powershell-5.1
# Get-PSSnapin
# Get-PSSnapin -Registered | Add-PSSnapin -Passthru

function global:myps1 {
   cd $env:USERPROFILE\sitebase\github\tpsup\ps1
}

Remove-Item -Path Alias:cd -ErrorAction Ignore
function global:cd {
   param ([String]$new = $null)

   [String]$saved_pwd = $pwd

   if (!$new) {
      Set-Location $home
   } elseif ($new -eq '-') {
      if ( $Env:old_pwd -eq '' ) {
         $Env:old_pwd = $pwd
      }
      Set-Location $Env:old_pwd
   } else {
      Set-Location $new
   }

   if ($?) {
      $Env:old_pwd = $saved_pwd
   }
}

function global:restorecd {
   Remove-Item -Path Function:cd

   # -scope global to make the alias available outside the function
   Set-Alias -Name cd -Value Set-Location -Scope global  
}

function global:kcd {
   # korn-shell-styled cd
   param (
      [String]$old_pattern = $null,
      [String]$new_pattern = $null
   )

   if (!$new_pattern) {
      Write-Host "Usage: kcd old_pattern new_patter"
      # don't exit
      return
   }

   [String]$new = ($pwd -replace ($old_pattern, $new_pattern))
   cd $new
}

function global:functions {
   Get-Item -Path Function:
}

function global:modules {
   Get-Module
   Write-Host "to see detail: Get-Module <mod name>|ConvertTo-Json)"
}

function global:tpsup {
   . $profile
}

function global:siteenv {
   # only global-scope var/function/alias will be effective after this function exits
   . $profile
}

function global:head {
   # unix head equivalent
   param ([String]$file = $null)
   Get-Content  $file -TotalCount 10
}

function global:voff {
   # turn off verbose
   $global:verbosePreference = "SilentlyContinue"
}

function global:AddPath {
    param([string]$var = $null,
          [string]$value = $null
          )
    if (!$value) {
       # Both !0 and !$null are $true, but $value is casted to string, therefore, $value can only be $null here.
       Write-Host "Usage: AddPath Var Value"
       return
    }
    [String] $old_string = (Get-Item -Path "Env:$var").Value
    $parts = $old_string -split ';'

    if (! ($parts -contains $value)) {
      Write-Verbose "adding to `$Env:PSModulePath: $value"
      $Env:PSModulePath += ";$value"
   }
}

function global:reduce {
   # simplify search paths
   param ([String]$var = $null,
          [String]$sep = $null,
          [Switch]$v = $false
          )

   if ($v) {
      $verbosePreference = "Continue"
   }

   $vars = @('Path', 'PSModulePath')
   if ($var) {
      $vars = @($var)
   }

   $sep_by_var = @{
      PATH = ';'
      PSMODULEPATH = ';'
   }

   foreach ($v2 in $vars) {
      [String] $string = (Get-Item -Path "Env:$v2").Value

      if (!$string) {
         Write-Verbose "`$Env:$v2 is empty"
         Continue
      }

      Write-Verbose "old `$Env:$v2 = $string"

      $separator = ';'
      if ($sep) {
         $separator = $sep
      } elseif ($sep_by_var.ContainsKey($v2.ToUpper())) {
         $separator = $sep_by_var[$v2.ToUpper()]
      }

      $seen_by_part = @{}
      $nonrepeat = New-Object System.Collections.Generic.List[System.String]
      $dropped = 0

      foreach ($part in ($string -split $separator)) {
         # Write-Verbose "parsing `$Env:$v2, part=$part"
         if ($seen_by_part.ContainsKey($part)) {
            Write-Verbose "`$Env:$v2 has dup $part, skipped"
            $seen_by_part[$part] += 1
            $dropped += 1
         } else {
            $nonrepeat.Add($part)
            $seen_by_part[$part] = 1
         }
      }

      if ($dropped) {
         $string = ($nonrepeat -join $separator)
         Set-Item -Path "Env:$v2" -Value $string
         Write-Verbose("new `$Env:$v2 = $string")
      } else {
         Write-Verbose("no change `$Env:$v2")
      }
   }
}

# set vi editor mode
# this works for powershell not powershell ISE
# https://serverfault.com/questions/36991/windows-powershell-vim-keybindings
$VIMEXEPATH    = "c:\cygwin64\bin\vim.exe"
Set-Alias vim  $VIMEXEPATH -Scope global
Set-Alias vi   $VIMEXEPATH -Scope global
Set-PSReadlineOption -EditMode vi

#Write-Host "To reload profile: siteenv"
#Write-Host "To auto complete var/function/command: tab"

