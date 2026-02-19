[CmdletBinding(PositionalBinding = $false)]

param(
    # [string]$outfile = $null,
    [switch]$kill,
    [Parameter(ValueFromRemainingArguments = $true)] $remainingArgs = $null
)
Set-StrictMode -Version Latest

$prog = ($PSCommandPath.Split('/\'))[-1]

# remove .ps1 extension
$prog = [System.IO.Path]::GetFileNameWithoutExtension($prog)

function usage {
    param([string]$message = $null)
    if ($message) { Write-Host $message }
    Write-Host "
Usage:
    ${prog} regex_pattern

    -k      Kill the matched processes.

Example:
    # print all processes
    ${prog} .

    # print c:\windows\system32\ processes
    ${prog} c:\\windows\\system32\\

    # kill all chrome processes from sitebase
    ${prog} -k \\sitebase\\.*\\chrome.exe

    # to handle both / and \ path separators, you can use a regex like this:
    ${prog} sitebase.*chrome

    powershell -ExecutionPolicy Bypass -File ./${prog}.ps1 regex_pattern
"
    exit 1
}
if (!$remainingArgs -or $remainingArgs.Count -ne 1) { usage ("wrong numnber of args") }
$pattern = $remainingArgs[0]

# build regex options
$regexOptions = [System.Text.RegularExpressions.RegexOptions]::Compiled

# add IgnoreCase
$regexOptions = $regexOptions -bor [System.Text.RegularExpressions.RegexOptions]::IgnoreCase

# the following only matches the process (program) name, not the command line. For example, it can match "chrome" but not "chrome.exe --remote-debugging-port=9222"
# Get-Process | Where-Object {
#     $_.ProcessName -match $pattern
# } | Select-Object Id, ProcessName, StartTime

try {
    $procs = Get-CimInstance Win32_Process -ErrorAction Stop   
} catch {
    Write-Verbose "Get-CimInstance failed, trying Get-WmiObject."
    $procs = Get-WmiObject -Class Win32_Process
}

# filter by regex on command line, not just process name.
$matches = foreach ($p in $procs) {
    $cmdline = $p.CommandLine
    if ([string]::IsNullOrEmpty($cmdline)) {
        continue
    }
    if ([System.Text.RegularExpressions.Regex]::IsMatch($cmdline, $pattern, $regexOptions)) {
        [PSCustomObject]@{
            PID = $p.ProcessId
            PPID = $p.ParentProcessId
            Name = $p.Name
            CommandLine = $cmdline
            ExcutablePath = $p.ExecutablePath
        }
    }
}

# $matches | Format-Table -AutoSize PID, PPID, Name, ExcutablePath
$matches | Format-Table -AutoSize PID, PPID, Name, CommandLine
if ($kill) {
    foreach ($m in $matches) {
        try {
            Stop-Process -Id $m.PID -Force
            Write-Host "Killed process $($m.PID) ($($m.Name))"
        } catch {
            Write-Warning "Failed to kill process $($m.PID): $_"
        }
    }
}
