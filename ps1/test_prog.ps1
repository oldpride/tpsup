[System.IO.Path]::GetTempPath()

write-Host ($PSCommandPath.Split('/\'))[-1]
Split-Path -Parent $PSCommandPath