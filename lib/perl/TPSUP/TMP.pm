package TPSUP::TMP;

use strict;
use warnings;
use Carp;
use Data::Dumper;

use base qw( Exporter );
our @EXPORT_OK = qw(
  get_tmp_file
);

my $tmp_index;

sub get_tmp_file {
   my ( $basedir, $prefix, $opt ) = @_;

   if ( $opt->{chkSpace} ) {
      my $os = 'uname -a';
      chomp $os;

      my $cmd = $os =~ /^Linux/ ? "df -kP $basedir" : "df -k $basedir";

      my @DF = `$cmd`;

      #Solaris 10$ df -k /var/tmp
      #Filesystem kbytes  used    avail    capacity Mounted on
      #/          4130542 2837486 1251751 70%      /

      if ( !$DF[1] ) {
         carp "cmd='$cmd' failed" . return undef;
      }

      chomp @DF;

      my @a = split /\s+/, $DF[1];

      my $avail = $a[3];

      $avail *= 1024;

      if ( $avail < $opt->{chkSpace} ) {
         carp
"$basedir doesn't have enough space, avail=$avail, require=$opt->{chkSpace}";
         return undef;
      }
   }

   my $id = `id`;
   my ($user) = ( $id =~ /^.+?\((.+?)\)/ );

   my $yyyymmdd = `date +%Y%m%d`;
   chomp $yyyymmdd;
   my $HHMMSS = `date +%H%M%S`;
   chomp $HHMMSS;

   my $tmpdir = "$basedir/tmp_${user}";
   my $daydir = "$tmpdir/$yyyymmdd";

   if ( !-d $daydir ) {
      system("mkdir -p $daydir");
      die "failed mkdir -p $daydir" if $?;

#system("find $tmpdir -mount -mtime +7 -exec /bin/rm -fr {} \\; 2>/dev/null");
# https://unix.stackexchange.com/questions/115863/delete-files-and-directories-by-their-names-no-such-file-or-directory
      system(
"find $tmpdir -mount -mtime +7 -prune -exec /bin/rm -fr {} \\; 2>/dev/null"
      );
   }

   if ( $opt->{AddIndex} ) {
      if ( !$tmp_index ) {
         $tmp_index = 1;
      } else {
         $tmp_index++;
      }
   }

   if ( $opt->{isDir} && "$opt->{isDir}" !~ /^[nf0]/i ) {
      my $dir = "$daydir/$prefix.$HHMMSS.$$.dir";

      $dir .= ".$tmp_index" if $opt->{AddIndex};

      mkdir($dir) || return undef;

      return $dir;
   } else {
      my $file = "$daydir/$prefix.$HHMMSS.$$";

      $file .= ".$tmp_index" if $opt->{AddIndex};

      return $file;
   }
}

1
