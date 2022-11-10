This folder is trying to make xterm working across all Linux.

Our Linux doesn't have xterm by default. I asked UNIX SA to have installed it
UNIX SA installed on one of the Linux box but the installed xterm only works with
that host's libc, ld, and xlibs.

The current folder creates a self-contained xterm version that can
be copied to all our Linux servers.

copied from

UNIX SA installed on this host
   $ uname -a
   Linux host1.abc.com 3.10.0-229.7.2.el7.x86_64 #1 SMP Fri May 15 21:38:46 EDT 2015 x86_64 x86_64 x86_64 GNU/Linux
   
   $ ldd /usr/bin/xterm
   linux-vdso.so.1 => (0x00007ffc69dfe000)
   libXft.so.2 => /lib64/libXft.so.2 (0x00007f84f87c8000)
   libfontconfig.so.1 => /lib64/libfontconfig.so.1 (0x00007f84f858a000)
   libXaw.so.7 => /lib64/libXaw.so.7 (0x00007f84f8325000)
   libXmu.so.6 => /lib64/libXmu.so.6 (0x00007f84f810a000)
   libXpm.so.4 => /lib64/libXpm.so.4 (0x00007f84f7ef7000)
   libICE.so.6 => /lib64/libICE.so.6 (0x00007f84f7cdb000)
   libXt.so.6 => /lib64/libXt.so.6 (0x00007f84f7a74000)
   libX11.so.6 => /lib64/libX11.so.6 (0x00007f84f7735000)
   libutempter.so.0 => /lib64/libutempter.so.0 (0x00007f84f7532000)
   libtinfo.so.5 => /lib64/libtinfo.so.5 (0x00007f84f7308000)
   libc.so.6 => /lib64/libc.so.6 (0x00007f84f6f46000)
   libfreetype.so.6 => /lib64/libfreetype.so.6 (0x00007f84f6ca0000)
   libXrender.so.l => /lib64/libXrender.so.l (0x00007f84f6a96000)
   libexpat.so.l => /lib64/libexpat.so.l (0x00007f84f686b000)
   libpthread.so.0 => /lib64/libpthread.so.0 (0x00007f84f664f000)
   libXext.so.6 => /lib64/libXext.so.6 (0x00007f84f643d000)
   libSM.so.6 => /lib64/libSM.so.6 (0x00007f84f6234000)
   libxcb.so.l => /lib64/libxcb.so.l (0x00007f84f6013000)
   libdl.so.2 => /lib64/libdl.so.2 (0x00007f84f5e0f000)
   /lib64/ld-linux-x86-64.so.2 (0x00007f84f89e9000)
   libuuid.so.l => /lib64/libuuid.so.l (0x00007f84f5c09000)
   libXau.so.6 => /lib64/libXau.so.6 (0x00007f84f5a05000)
   
   $ ldd /usr/bin/xrdb
   linux-vdso.so.l => (0x00007fffa17fe000)
   libXmuu.so.l => /lib64/libXmuu.so.l (0x00007f2e716e2000)
   libXll.so.6 => /lib64/libXll.so.6 (0x00007f2e713a3000)
   libc.so.6 => /lib64/libc.so.6 (0x00007f2e70fe2000)
   libxcb.so.l => /lib64/libxcb.so.l (0x00007f2e70dc1000)
   libdl.so.2 => /lib64/libdl.so.2 (0x00007f2e70bbc000)
   /lib64/ld-linux-x86-64.so.2 (0x00007f2e718f2000)
   libXau.so.6 => /lib64/libXau.so.6 (0x00007f2e709b8000)
   
The following files will be enough
   ./usr/bin/xrdb
   ./usr/bin/xterm
   ./usr/share/X11/app-defaults
   ./usr/share/X11/app-defaults/XTerm-color
   ./usr/share/X11/app-defaults/XTerm
   ./usr/share/X11/locale
   ,/lib64/libxcb.so.1.1.0
   ./lib64/libXext.so.6.4.0
   ./lib64/libXrender.so.1.3.0
   ./lib64/libpthread.so.0
   ./lib64/libexpat.so.1
   ./lib64/libfreetype.so.6.10.0
   ./lib64/libXaw7.so.7.0.0
   ./lib64/libSM.so.6
   ./lib64/libX11.so.6.3.0
   ./lib64/libtinfo.so.5
   ./lib64/ld-2.17.so
   ./lib64/libpthread-2.17.so
   ./lib64/libxcb.so.1
   ./lib64/libXau.so.6
   ./lib64/libXmu.so.6
   ./lib64/libXft.so.2.3.2
   ./lib64/libdl.so.2
   ./lib64/libtinfo.so.5.9
   ./lib64/libfontconfig.so.1.7.0
   ./lib64/libut empt er.so.1.1.6
   ./lib64/libXft.so.2
   ./lib64/libXt.so.6
   ./lib64/libuuid.so.1.3.0
   ./lib64/libutempt er.so.0
   ./lib64/libc.so.6
   ./lib64/libdl-2.17.so
   ./lib64/libXpm.so.4.11.0
   ./lib64/libexpat.so.1.6.0
   ./lib64/libXt.so.6.0.0
   ./lib64/libXaw.so.7
   ./lib64/libXau.so.6.0.0
   ./lib64/libXrender.so.1
   ./lib64/libuuid.so.1
   ./lib64/libICE.so.6
   ./lib64/libSM.so.6.0.1
   ./lib64/libICE.so.6.3.0
   ./lib64/libXcursor.so.1
   ./lib64/libX11.so.6
   ./lib64/libXmu.so.6.2.0
   ./1ib64/libXaw7.so.7
   ./lib64/libXcursor.so.1.0.2
   ./lib64/libfontconfig.so.1
   ./lib64/libfreetype.so.6
   ./lib64/ld-linux-x86-64.so.2 (a link to ld-2.17.so)
   ./lib64/libc-2.17.so
   ./lib64/libXpm.so.4

   On RedHat/Sussex, all linked libs should be under /usr/lib64 or /lib64.
   If you see /usr/lib or /lib, that will be wrong as these are 32-bit libs.
   
   On ubuntu, the 64-bit libs are under /usr/lib

to run xterm on a new host
   ROOT=$TPSUP/Linux/Linux3
   
   export XFILESEARCHPATH=$ROOT/usr/share/X11/app-defaults/%N
   export XLOCALEDIR=$ROOT/usr/share/X11/locale
   $ROOT/lib64/ld-2.17.so --library-path $ROOT/lib64 $ROOT/usr/bin/xterm -display test.db.com:6000
   
to ldd:
   LD_TRACE_LOADED_OBJECTS=1 $ROOT/lib64/ld-2.17.so --library-path $ROOT/lib64 $ROOT/usr/bin/xterm -display test.db.com:6000

to trace: (note: don't use $ROOT/usr/bin/strace)
   strace $ROOT/lib64/ld-2.17.so --library-path $ROOT/lib64 $ROOT/usr/bin/xterm -display test.db.com:6000
   
