[System.IO.Path]::GetTempPath()

Write-Host ($PSCommandPath.Split('/\'))[-1]
Split-Path -Parent $PSCommandPath
