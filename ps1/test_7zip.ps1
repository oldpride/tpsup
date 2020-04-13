[CmdletBinding(PositionalBinding=$false)] param (
    [switch]$v                                   = $false,
    [Alias("c")][switch]$create                  = $false,
    [Alias("x")][switch]$extract                 = $false,
    [Parameter(Mandatory = $true)][Alias("f")][string]$file        = $null,
    [Parameter(ValueFromRemainingArguments = $true)]$remainingArgs = $null
)


# https://stackoverflow.com/questions/38776137/native-tar-extraction-in-powershell


function Expand-Tar($tarFile, $dest) {

    $pathToModule = "$HOME\ps1m\7Zip4Powershell\1.10.0.0\7Zip4PowerShell.psd1"

    if (-not (Get-Command Expand-7Zip -ErrorAction Ignore)) {
        Import-Module $pathToModule
    }

    Expand-7Zip $tarFile $dest
}

$dir = $remainingArgs[0]

Expand-Tar $file $dir

#test_7zip -f C:\Users\william\AppData\Local\Temp\tmp635B.tar $HOME\tmpdir