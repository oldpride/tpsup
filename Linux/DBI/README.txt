This is specific to Linux. Linux's release makes its libc and ld not backward|compatible.

This is to make DBI/DBD Oracle work on Linux, in particular

   tpsup/scripts/sql.
   tpsup/lib/perl/Linux/lib/perl5/site_perl/5.10.0/x86_64-linux-thread-multi/auto/DBD/Oracle/Oracle.so

requires specific libc, ld, and oracle lib. So this folder is trying to solve the
compatibility problem, to make a self-contained minimal oracle client.

(later applied the same strategy to make sybase and tibrv work)

copied from a host that UNIX SA installed .../ORCLclnt/product/10.2.0.3

The following files are copied from that host
$ find .

./DBtibrv/7.3/include
./DBt ibrv/7.3/include/t ibrv
./DBtibrv/7.3/lib
./DBtibrv/7.3/lib/libtibrv64.so
./DBtibrv/7.3/lib/libtibrvcm64.so
./lib64/ld-linux-x86-64.so.2
./lib64/libcrypt.so.l
./lib64/libc.so.6
./lib64/libdl.so.2
./lib64/libm.so.6
./lib64/libnsl-2.11.3.so
./lib64/libnsl.so.l
./lib64/libpthread.so.0
./ORCLclnt/product/10.2.0.3/lib
./ORCLclnt/product/10.2.0.3/oracore
./SYBSclnt/12.5.l_64bit/sybase/charsets
./SYBSclnt/12.5.l_64bit/sybase/config
./SYBSclnt/12.5.l_64bit/sybase/locales
./SYBSclnt/12.5.l_64bit/sybase/OCS-12_5
./usr/bin/perl
./usr/lib/perl5/5.10.0
./usr/lib/perl5/site_perl

The following is in tpsup/scripts/sql.linux
ROOT=$TPSUP/Linux/DBI

export ORACLE_HOME=$TPSUP/Linux/DBI/ORCLclnt/product/10.2.0.3

export PERL5LIB=$TPSUP/lib/perl:$TPSUP/lib/perl/Linux/lib/perl5/5.10.0:\
                $TPSUP/lib/perl/Linux/lib/perl5/site_perl/5.10.0:\
                $TPSUP/lib/perl/Linux/lib/perl5/site_perl/5.10.0/x86_64-linux-thread-multi:\
                $TPSUP/Linux/DBI/usr/lib/perl5/5.10.0

export SYBVER=12.5.1_64bit
export SYBASE_OCS=OCS-12_5

export SYBASE=$TPSUP/Linux/DBI/SYBSclnt/12.5.1_64bit/sybase
export LD_LIBRARY_PATH=$TPSUP/Linux/DBI/SYBSclnt/12.5.l_64bit/sybase/OCS-12_5/lib:$LD_LIBRARY_PATH

$ROOT/lib64/ld-linux-x86-64.so.2 --library-path $ROOT/lib64:$LD_LIBRARY_PATH $ROOT/usr/bin/perl $TPSUP/scripts/sql "$@"

