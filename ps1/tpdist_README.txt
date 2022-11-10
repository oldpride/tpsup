2022/08/09
tpdist.ps1 got antivirus warning

   This script contains malicious content and has been blocked by your antivirus software.

note: the complained line number was always the first line. It didn't tell which line really triggered the alert.

by removing lines (binary search) I found the antivirus software didn't like the expect_socket().

So I separated it into two files
   tpdist2_main.ps1
   tpdist2_expect_socket.ps1

Now tpdist2_main.ps1 would do the work.
