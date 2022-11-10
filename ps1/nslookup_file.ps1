# PS C:\Users\william\sitebase\github\tpsup\ps1> nslookup_file.ps1 C:\Users\william\sitebase\github\tpsup\ps1\nslookup_file_test.txt

# HostName                Aliases AddressList
# --------                ------- -----------
# tianpc                  {}      {192.168.96.1, 192.168.1.179}
# linux1.fios-router.home {}      {192.168.1.191}
# 
# PS C:\Users\william\sitebase\github\tpsup\ps1> nslookup_file.ps1 nslookup_file_test.txt
# 
# HostName                Aliases AddressList
# --------                ------- -----------
# tianpc                  {}      {192.168.96.1, 192.168.1.179}
# linux1.fios-router.home {}      {192.168.1.191}
# 
# save a list of hostnames into a file
#
param(
[string]$file
)

#$list = gc -Path C:\temp\server.txt
$list = gc -Path $file
foreach ($server in $list) {
   [system.net.dns]::resolve($server)
}


