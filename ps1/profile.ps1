# add the following in $profile, eg,
# function global:tpsup {
#     . C:\Users\william\sitebase\github\tpsup\ps1\profile.ps1
# }
# profiles are:
#    C:\Users\william\Documents\WindowsPowerShell\Microsoft.PowerShell_profile.ps1
#    C:\Users\william\Documents\WindowsPowerShell\Microsoft.PowerShellISE_profile.ps1

$global:TPPS1=(Split-Path -Parent $PSCommandPath)
$global:TPSUP=(Split-Path -Parent $TPPS1)

# don't update $env:var directly as it is like setx: it permanently set the variable. for example
#   $env:Path += ";$TPPS1"
#   $env:PSModulePath += ";$TPPS1" + ";$HOME"
# instead, use the following command to set it in the process level
#   [System.Environment]::SetEnvironmentVariable('var', 'value',[System.EnvironmentVariableTarget]::Process)
# the above command is wrapped in addpath.

# https://docs.microsoft.com/en-us/powershell/module/microsoft.powershell.core/add-pssnapin?view=powershell-5.1
# Get-PSSnapin
# Get-PSSnapin -Registered | Add-PSSnapin -Passthru

function global:sitebase {
    cd $SITEBASE
}

function global:myps1 {
    cd $TPPS1
}

function global:mysamba {
    cd Z:
}

function global:mysite {
    cd $SITESPEC/ps1
}

function global:mytp {
    cd $TPPS1
}


#Set-PsDebug -Trace 1
Remove-Item -Path Alias:cd -ErrorAction Ignore
#get-command cd
function global:cd {
    param([string]$new = $null)

    [string]$saved_pwd = $pwd

    if (!$new) {
        Set-Location $home
    } elseif ($new -eq '-') {
        if ($Env:old_pwd -eq '') {
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
#Set-PsDebug -Trace 0

function global:restorecd {
    Remove-Item -Path Function:cd

    # -scope global to make the alias available outside the function
    Set-Alias -Name cd -Value Set-Location -Scope global
}

function global:kcd {
    # korn-shell-styled cd
    param(
        [string]$old_pattern = $null,
        [string]$new_pattern = $null
    )

    if (!$new_pattern) {
        Write-Host "Usage: kcd old_pattern new_patter"
        # don't exit
        return
    }

    [string]$new = ($pwd -replace ($old_pattern,$new_pattern))
    cd $new
}

function global:functions {
    Get-Item -Path Function:
}

function global:modules {
    Get-Module
    Write-Host "to see detail: Get-Module <mod name>|ConvertTo-Json)"
}

function global:reimport {
    param(
        [string]$module = $null
    )

    if (!$module) {
        Write-Host "Usage: reimport <module>"
        # don't exit
        return
    }
    Remove-Module $module
    Import-Module $module
}

function global:tpsup {
    . $TPPS1/profile.ps1
}

function global:siteenv {
    # only global-scope var/function/alias will be effective after this function exits
    . $TPPS1/profile.ps1
}

<#
# we created a head.ps1
function global:head {
    # unix head equivalent
    param([string]$file = $null)
    Get-Content $file -TotalCount 10
}
#>

function global:voff {
    # turn off verbose
    $global:verbosePreference = "SilentlyContinue"
}

function global:unset {
    Write-Host "
    To unset a function: Remove-Item -Path Function:func_name
    "
}

function global:findscope {
    param([string]$var = $null,
        [switch]$v     = $false
    )
    
    if (!$var) {
        Write-Host "ERROR: wrong number of args"
        Write-Host "USAGE: findscope var_name"
        return
    }

    Write-Host "Machine Scope: $([System.Environment]::GetEnvironmentVariable($var,[System.EnvironmentVariableTarget]::Machine))`n"
    Write-Host "User    Scope: $([System.Environment]::GetEnvironmentVariable($var,[System.EnvironmentVariableTarget]::User))`n"
    Write-Host "Process Scope: $([System.Environment]::GetEnvironmentVariable($var,[System.EnvironmentVariableTarget]::Process))`n"
}

function global:AddPath {
    param([string]$var = $null,
        [string]$value = $null,
        [switch]$v     = $false
    )
    if (!$value) {
        # Both !0 and !$null are $true, but $value is casted to string, therefore, $value can only be $null here.
        Write-Host "Usage: AddPath Var Value"
        return
    }

    if ($v) {
        $verbosePreference = "Continue"
    }

    [string]$string = $null    
    try {
        $string = (Get-Item -Path "Env:$var").Value
        Write-Verbose "old `$Env:$var=$string"
    } catch {
        $string = ""
        Write-Verbose "Env:$Var doesn't exist"
    }   
    
    $added = 0 
    # powershell is fundamentally case-insensitive
    #    PS> "a" -eq "A"
    #    True
    if ($string -eq ""){
        $string += "$value"
        $added ++
    } else {
        $parts = $string -split ';'
        if (!($parts -contains $value)) {   
            $string += ";$value"
            $added ++
        }
    }

    if ($added) {
        Write-Verbose "adding to `$Env:$var $value"
        Write-Verbose "new `$Env:$var=$string"
        # this will set User-level (scope), basically permanent set. but we only want temporary setting, for this process and children
        # Set-Item -Path "Env:$var" -Value "$string"
        [System.Environment]::SetEnvironmentVariable($var, $string,[System.EnvironmentVariableTarget]::Process)
    } else {
        Write-Verbose "no change `$Env:$var"
    }
}

function global:beaut {
    param([Parameter(ValueFromRemainingArguments = $true)] $remainingArgs = $null
    )

    [string]$myfunc = $MyInvocation.MyCommand
    if (!$remainingArgs) {
        Write-Host "Usage: $myfunc file1.ps1 file2.ps1 ..."
        Write-Host "       $myfunc *.ps1"
        return
    }

    foreach ($pattern in $remainingArgs) {
        Write-Host "pattern: $myfunc $pattern"
        foreach ($f in (Get-ChildItem $pattern)) {
            Write-Host "file: $myfunc $f"
            Edit-DTWBeautifyScript -IndentType Fourspaces -NewLine LF $f
        }
    }
}

function global:env {
    Get-ChildItem Env:
}

function global:reduce {
    # simplify search paths$myfunc
    param([string]$var = $null,
        [string]$sep = $null,
        [switch]$v = $false
    )

    if ($v) {
        $verbosePreference = "Continue"
    }

    $vars = @('Path','PSModulePath')
    if ($var) {
        $vars = @($var)
    }

    $sep_by_var = @{
        Path = ';'
        PSMODULEPATH = ';'
    }

    foreach ($v2 in $vars) {
        [string]$string = (Get-Item -Path "Env:$v2").Value

        if (!$string) {
            Write-Verbose "`$Env:$v2 is empty"
            continue
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
            Write-Verbose ("new `$Env:$v2 = $string")
        } else {
            Write-Verbose ("no change `$Env:$v2")
        }
    }
}

# "The call operator (&) always uses a new scope. Instead, use the dot source (.) operator:"
# https://stackoverflow.com/questions/63551546/powershell-remove-item-not-working-from-a-function
# TODO, replace the following with "." source. 
addpath Path $TPPS1
reduce "Path"
reduce "PSModulePath"

# set vi editor mode
# this works for powershell not powershell ISE
# https://serverfault.com/questions/36991/windows-powershell-vim-keybindings
$VIMEXEPATH = "c:\cygwin64\bin\vim.exe"
Set-Alias vim $VIMEXEPATH -Scope global
Set-Alias vi $VIMEXEPATH -Scope global
Set-PSReadLineOption -EditMode vi

#Write-Host "To reload profile: siteenv"
#Write-Host "To auto complete var/function/command: tab"

function global:selenium {
    # add path for chrome and chromedriver
    addpath Path "C:\Program Files (x86)\Google\Chrome\Application"   
    get-command chrome

    addpath Path $HOME  
    get-command chromedriver
}

function global:p3env {
    addpath PYTHONPATH "$TPSUP\python3\lib" 
}

function global:p3scripts {
    cd  "$TPSUP\python3\scripts" 
}
