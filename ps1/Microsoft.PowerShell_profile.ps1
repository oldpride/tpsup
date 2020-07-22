$env:Path = "C:\Program Files (x86)\Common Files\Oracle\Java\javapath;C:\Program Files\Python37\Scripts\;C:\Program Files\Python37\;C:\WINDOWS\system32;C:\WINDOWS;C:\WINDOWS\System32\Wbem;C:\WINDOWS\System32\WindowsPowerShell\v1.0\;C:\WINDOWS\System32\OpenSSH\;C:\src\flutter\bin;C:\Program Files\Git\cmd;C:\Program Files\Intel\WiFi\bin\;C:\Program Files\Common Files\Intel\WirelessCommon\;C:\Program Files\PuTTY\;C:\Users\william\AppData\Local\Microsoft\WindowsApps;C:\Users\william\AppData\Local\Android\Sdk\platform-tools;C:\Users\william\AppData\Local\Android\Sdk\emulator;;C:\Program Files\JetBrains\PyCharm Community Edition 2019.1.3\bin;C:\users\william\sitebase\github\tpsup\ps1"
#$env:Path



[Environment]::SetEnvironmentVariable("Path", $env:Path, "User")
#[Environment]::GetEnvironmentVariable("Path", "User")

# https://docs.microsoft.com/en-us/powershell/module/microsoft.powershell.core/add-pssnapin?view=powershell-5.1
# Get-PSSnapin
# Get-PSSnapin -Registered | Add-PSSnapin -Passthru

function myps1 {
   cd $env:USERPROFILE\sitebase\github\tpsup\ps1
}

Remove-Item -Path Alias:cd
function cd {
   
}

function restorecd {
   Remove-Item -Path Function:cd
   Set-Alias -Name cd -Value Set-Location
}

function functions {
   Get-Item -Path Function:
}

Write-Host "To reload profile: . `$profile"
