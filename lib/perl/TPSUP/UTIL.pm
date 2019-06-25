package TPSUP::UTIL;

use strict;
use base qw( Exporter );
our @EXPORT_OK = qw(
   get_tmp_file
   get_in_fh
   get_out_fh
   tpeng_lock
   tpeng_unlock
   get_patterns_from_log
   cp_file2_to_file1
   backup_filel_to_file2
   expect_socket
   get_abs_path
   get_abs_cwd
   get_exps_from_string
   get_ExpHash_from_ArrayOfStrings
   get_user
   get_homedir_by_user
   recursive_handle
   transpose_arrays
   compile_perl
   compile_perl_array
   compile_paired_strings
   chkperl
   tpfind
   recursive_path
   get_user_by_uid
   get _group_by_gid
   insert_namespace_code
   insert_namespace_file
   insert_namespaces
   unique_array
   sort_unique
   trim_path
   reduce_path
   get_items_from_file
   get_pw_by_key
   get_java
   glob2regex
);

use Carp;
use Data::Dumper;
use IO::Select;
use Cwd;
use Cwd 'abs_path';
use TPSUP::Expression;

my $tmp_index;

sub get_tmp_file {
   my ($basedir, $prefix, $opt) = @_;

   if ($opt->{chkSpace}) {
      my $os = 'uname -a'; chomp $os;

      my $cmd = $os=~/^Linux/ ? "df -kP $basedir" : "df -k $basedir";
      
      my @DF = `$cmd`;
      
      #Solaris 10$ df -k /var/tmp
      #Filesystem kbytes  used    avail    capacity Mounted on
      #/          4130542 2837486 1251751 70%      /
      
      if ( ! $DF[1]) {
         carp "cmd='$cmd' failed".
         return undef;
      }
      
      chomp @DF;
      
      my @a = split /\s+/, $DF[1];
      
      my $avail = $a[3];
      
      $avail *= 1024;
      
      if ($avail < $opt->{chkSpace}) {
         carp "$basedir doesn't have enough space, avail=$avail, require=$opt->{chkSpace}";
         return undef;
      }
   }
   
   my $id = `id`;
   my ($user) = ($id =~ /^.+?\((.+?)\)/ );

   my $yyyymmdd = `date +%Y%m%d`; chomp $yyyymmdd;
   my $HHMMSS   = `date +%H%M%S`; chomp $HHMMSS;
   
   my $tmpdir = "$basedir/tmp_${user}";
   my $daydir = "$tmpdir/$yyyymmdd";
   
   if (! -d $daydir ) {
      system("mkdir -p $daydir");
      die "failed mkdir -p $daydir" if $?;
      system("find $tmpdir -mount -mtime +7 -exec /bin/rm -fr {} \\; 2>/dev/null");
   }
   
   if ($opt->{AddIndex}) {
      if (!$tmp_index) {
         $tmp_index = 1;
      } else {
        $tmp_index++;
      }
   }
   
   if ($opt->{isDir} && "$opt->{isDir}" !~ /^[nf0]/i) {
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
   
sub get_in_fh {
   my ($input, $opt) = @_;
   
   my $in_fh;
   
   if (!defined($input) || $input eq '-') {
      $in_fh = \*STDIN;
      $opt->{verbose} && print STDERR "get_in_fh() opened STDIN\n";
   } else {
      my $cmd;
   
      my ($host, $path);
   
      my $ssh_host;
   
      if ($input =~ m|^([^/]+?):(.+)|) {
         # user@hostname:tpsup/profile
         ($host, $path) = ($1, $2);

         $ssh_host = "ssh -n -o StrictHostKeyChecking=no -o ConnectTimeout=5 -o BatchMode=yes $host";
      } else {
         $ssh_host = "";
         $path = $input;
   
         croak "$input is not found or is not a file" if ! -f $input;
      }
   
      if ($path =~ /gz$/) {
         {
            my $cmd = "$ssh_host gunzip -c $path";
            $opt->{verbose} && print STDERR "cmd=$cmd\n";
            open $in_fh, "$cmd|" or croak "cmd=$cmd failed: $!";
         }
      } else {
         if ($ssh_host) {
            my $cmd = "$ssh_host cat $path";
            $opt->{verbose} && print STDERR "cmd=$cmd\n";
            open $in_fh, "$cmd|" or croak "cmd=$cmd failed: $!";
         } else {
            $opt->{verbose} && print STDERR "cmd=<$path\n";
            open $in_fh, "<$path" or croak "cannot read $path";
         }
      }
   }
   
   return $in_fh;
}
   
sub get_out_fh {
   my ($output, $opt) = @_;
   
   my $out_fh;
   
   if (!defined($output) || $output eq '-') {
      $out_fh = \*STDOUT;
   } else {
      my ($outdir) = ($output =~ m:/^(.+/):);

      if (!defined($outdir) || ! "$outdir" ) {
         $outdir = ".";
      }

      if (! -d $outdir) {
         system("mkdir -p $outdir");

         croak "cannot mkdir -p $outdir" if $?;
      }
   
      if ($opt->{AppendOutput}) {
         open $out_fh, ">>$output" or croak "cannot append to $output: $!";
      } else {
         open $out_fh, ">$output" or croak "cannot write to $output: $!";
      }
   }

   return $out_fh;
}
   
sub get_items_from_file {
   my ($file, $opt) = @_;
   
   my $ifh = get_in_fh($file, $opt) ;
   
   my $ret;

   my $delimiter = $opt->{InlineDelimiter};
   
   if (defined $delimiter) {
      # multiple items per line
      while (<$ifh>) {
         chomp;

         next if /^\s*$|^\s*#/;
   
         my $line = $_;
   
         for my $e (split /$delimiter/, $line) {
            next if !defined $e || "$e" eq "";
            $ret->{$e} ++;
         }
      }
   } else {
      # default to one item per line
      while (<$ifh>) {
         chomp;

         next if /^\s*$|^\s*#/;
   
         $ret->{$_} ++;
      }
   }
   
   close $ifh if $ifh != \*STDIN;
   
   return $ret;
}
   
sub tpeng_lock($;$) {
   my $MAGIC = 'AccioConfundoLumosNox';
   my $len = length($_[0]);
   my $salt = $_[1] || $MAGIC;
   my $magic = substr( $salt x $len, 0, $len );

   return uri_escape($_[0]^$magic);
}
   
sub tpeng_unlock($;$) {
   my $MAGIC = 'AccioConfundoLumosNox';
   my $dec = uri_unescape($_[0]);
   my $salt = $_[1] || $MAGIC;
   my $len = length($dec);
   my $magic = substr( $salt x $len, 0, $len );

   return $dec^$magic;
}
    
sub get_pw_by_key {
   my ($key, $opt) = @_;
   
   my $book;
   
   if ($opt->{book}) {
      $book = $opt->{book};
   } else {
      my $homedir = (getpwuid($<))[7];
      my $hiddendir = "$homedir/.tpsup";
      $book = "$hiddendir/book.csv";
   }
   
   croak "$book not found" if ! -f $book;
   
   my $file_mode = sprintf("%04o", (stat($book))[2] & 07777);
   croak "$book permissions is $file_mode not expected 0600\n" if "$file_mode" ne "0600";
   
   open my $fh, "<$book" or croak "cannot read $book";
   
   my $header = <$fh>; chomp $header;
   
   my $expected = "key,string,comment";
   
   croak "$book has unexpected header='$header'. expected='$expected'" if $header ne $expected;
   while (<$fh>) {
      next if /^\s*$/;
      next if /^\s*#/;
   
      my ($k, $string, $comment) = split /,/;
   
      next if $k ne $key;

      next if ! $string;
   
      my $pw = tpeng_unlock($string);
   
      return $pw;
   }
   
   return undef;
}
   
######################################################################################
# begin: extracted from
# .../perl5/site_perl/5.10.0/URI/Escape.pm
   
sub uri_escape {
   my($text) = @_;
   
   return undef unless defined $text;

   # Build a. char->hex map
   my %escapes;
   for (0..255) {
      $escapes{chr($_)} = sprintf("%%%02X", $_);
   }
   
   my $RFC3986 = qr/[^A-Za-z0-9\-\._~]/;

   $text =~ s/($RFC3986)/$escapes{$1} || _fail_hi($1)/ge;
   
   $text;
}
   
sub uri_unescape {
   # Note from RFC1630: "Sequences which start with a percent sign
   # but are not followed by two hexadecimal characters are reserved
   # for future extension"
   my $str = shift;
   if (@_ && wantarray) {
      # not executed for the common case of a single argument
      my @str = ($str, @_); # need to copy
      for (@str) {
         s/%([0-9A-Fa-f]{2})/chr(hex($1))/eg;
      }
      return @str;
   }
   $str =~ s/%([0-9A-Fa-f]{2})/chr(hex($1))/eg if defined $str;
   $str;
}
   
sub _fail_hi {
   my $chr = shift;
   Carp::croak(sprintf "Can't escape \\x{%04X)", ord($chr));
}
   
# end: extracted from
# .../perl5/site_perl/5.10.0/URI/Escape.pm
#################H######HH#####H#############H########H###################H####
   
sub get_patterns_from_log {
   my ($log, $match_pattern, $opt) = @_;
   
   my $exclude_pattern = $opt->{ExcludePattern};
   
   my $ErasePattern = defined $opt->{ErasePattern} ? qr/$opt->{ErasePattern}/ : undef;
   my $BeginPattern = defined $opt->{BeginPattern} ? qr/$opt->{BeginPattern}/ : undef;
   my $EndPattern   = defined $opt->{EndPattern}   ? qr/$opt->{EndPattern}/   : undef;
   
   my $fh = get_in_fh($log);
   
   my $ret;

   my $begun;
   my $end;
      
   while (<$fh>) {
      my $line = $_;
      
      chomp $line;
      
      last if $end;
      
      if ($BeginPattern && !$begun) {
         if ($line =~ /$BeginPattern/) {
            $begun ++;
         } else {
            next;
         }
      }
      
      if ($EndPattern) {
         if ($line =~ /$EndPattern/) {
            $end ++;
         }
      }
      
      next if defined $exclude_pattern && $line =~ /$exclude_pattern/;
      
      next if $line !~ /$match_pattern/;
      
      my $pattern = $line;
      
      #$pattern =~ s/\d+/./g; # convert number into .
      
      if ($ErasePattern) {
         $pattern =~ s/$ErasePattern/./g;
      }
      
      if (! $ret->{$pattern}) {
         $ret->{$pattern}->{first} = $line;
         $ret->{$pattern}->{count} ++;
      } else {
         $ret->{$pattern}->{last} = $line;
         $ret->{$pattern}->{count} ++;
      }
   }
      
   close $fh if $fh != \*STDIN;
      
   return $ret;
}
      
sub cp_file2_to_file1 {
   # overwrite file1 with file2's content
   my ($file2, $file1, $opt) = @_;

   if ($opt->{ShowDiff}) {
      my $cmd = "diff $file1 $file2";
      
      $opt->{PrintCmd} && print "Diff cmd - $cmd\n";
      my $diff_rc = system("$cmd");
      $diff_rc = $diff_rc >> 8;
      
      if (!$diff_rc) {
         print "No difference\n";
         return "No change because no difference";
      }
   }
      
   if (!$opt->{NoPrompt}) {
      print "Do you want to make this change? Y/N [N]\n";
      my $answer = readline(*STDIN);
      
      if ($answer !~ /^\s*[yY]/) {
         return "You didn't answer yes, meaning not to change";
      }
   }
      
   if (!$opt->{NoBackup}) {
      my ($package, $prog, $line) = caller;
      
      $prog =~ s:.*/::;
      
      my $tmpfile = get_tmp_file("/var/tmp", "${prog}", {AddIndex=>1});
      
      my $rc = backup_file1_to_file2($file1, $tmpfile, $opt);

      return "Backup failed" if $rc;
   }
      
   my $cmd = "/bin/cp $file2 $file1";
      
   $opt->{PrintCmd} && print "Copy cmd - $cmd\n";
      
   my $rc = system($cmd);
      
   if ($rc) {
      return "Update failed";
   } else {
      return "Updated";
   }
}
      
sub backup_file1_to_file2 {
   my ($file, $backup, $opt) = @_;

   my $cmd = "/bin/cp $file $backup";
   
   $opt->{PrintCmd} && print "Backup cmd = $cmd\n";
   
   my $rc = system($cmd);
   
   return $rc;
}
   
sub get_abs_path {
   my ($path) = @_;
   
   # $ perl -e 'use Cwd 'abs_path'; print abs_path("tpsup/scripts/../autopath"), "\n";'
   # /home/gpt/tpsup/autopath
   # $ perl -e 'use Cwd 'abs_path'; print abs_path("./tpsup/scripts/../autopath"), "\n";'
   # /home/gpt/tpsup/autopath
   # $ perl -e 'use Cwd 'abs_path'; print abs_path(".//tpsup/scripts/../autopath/"), "\n";'
   # /home/gpt/tpsup/autopath
   
   return abs_path($path);
}
   
sub get_abs_cwd {
   my $cwd = getcwd();
   
   return abs_path($cwd);
}
   
my $user;
sub get_user {
   return $user if $user;
   
   my $line = `id`;
   
   #uid=9020(tian) gid=7296(unix)
   
   ($user) = ( $line =~ /^.+?\((.+?)\)/ );
   
   die "cannot figure out user from 'id' command: $line" if !$user;
   
   return $user;
}
   
my $homedir_by_user;

sub get_homedir_by_user {
   my ($user) = @_;
   
   $user = get_user() if !$user;
   
   # http://stackoverflow.com/questions/3526420/how-do-i-get-the-current-user-in-perl-in-a-portable-way
    
   return $homedir_by_user->{$user} if exists $homedir_by_user->{$user};
   
   my $line = `getent passwd $user`;
   
   if (!$line) {
      $homedir_by_user->{$user} = undef;
      return undef;
   }
   
   #tian:x:9020:7296:UNIX User,APP,2254201:/home/tian:/bin/ksh
   
   my @a = split /:/, $line;
   
   my $homedir = $a[5];
   
   $homedir_by_user->{$user} = $homedir;
   
   return $homedir;
}
   
sub expect_socket {
   my ($socket, $patterns, $opt) = @_;
   
   my $type = ref $patterns;
   croak "\$patterns must be ref to ARRAY, yours is $type" if $type ne 'ARRAY';

   my $interval = $opt->{ExpectInterval} ? $opt->{ExpectInterval} : 30;
   
   my $total_data;
   my @matched;
   my @captures;
   
   my $select = IO::Select->new($socket) or die "IO::Select $!";
   
   my $num_patterns = scalar(@$patterns);
   my $total_wait = 0;
   
   while (1) {
      if (! $select->can_read($interval)) {
         if ($opt->{ExpectTimeout}) {
            $total_wait += $interval;
   
            if ($total_wait >= $opt->{ExpectTimeout}) {
               print STDERR "expect_socket timed out after $opt->{ExpectTimeout} seconds\n";
               return (\@matched, \@captures, {status=>'timed out'});
            }
         }

         next;
      }
   
      my $data;

      my $size = read($socket, $data, 1024000);
      
      if (!$size) {
         my $total_size = length($total_data);
         my $print_size = $total_size - 100 < 0 ? $total_size : 100;
      
         my $last_words = substr $total_data, $total_size-$print_size, $print_size;
      
         $opt->{verbose} && print STDERR "Socket closed. Last words from peer: ... $last_words\n";
         return (\@matched, \@captures, {status=>'closed'});
      } else {
         $opt->{verbose} && print STDERR "received data: $data\n";
      
         $total_data .= $data;
      
         my $all_matched = 1;
      
         for (my $i=0; $i<$num_patterns; $i++) {
            next if $matched[$i];
      
            if ($total_data =~ /$patterns->[$i]/s) {
               $opt->{verbose} && print STDERR "matched $patterns->[$i]\n";
      
               $matched[$i] = 1;
               $captures[$i] = [$1, $2, $3];
            } else {
               $all_matched = 0;
            }
         }
      
         return (\@matched, \@captures, {status=>"done"}) if $all_matched;
      }
   } 
}
      

sub get_exps_from_string {
   my ($string, $opt) = @_;
      
   my $delimiter = $opt->{delimiter} ? $opt->{delimiter} : ',';
      
   # ${55),substr(${126),4,6),substr("abc",1,1),...
   # CumQty=${14),Price=sprintf("%.2f",${44}),Open/Close=${77}
      
   my @a = split //, $string;
      
   my @exps;
   my $current_exp = '';
   my @nesttings; #parenthsis nests
   my $quote_char;
   my $quote_pos;

   my $i=0;

   for my $c (@a) {
      $i++; #$i effectively starts from 1

      if ($quote_char) {
         # a quote already started

         $current_exp .= $c;
      
         if ($c eq $quote_char) {
            # this is a closing quote: " matches " or ' matches '.
            $quote_char = '';
         }
      
         next;
      }
      
      if ($c eq "'" || $c eq '"') {
         # starts a new quote
         $current_exp .= $c;
      
         $quote_char = $c;
      
         $quote_pos = $i;
      
         next;
      }
      
      if ($c eq '(') {
         # starts a new nest
      
         $current_exp .= $c;
      
         push @nesttings, $i;
      
         next;
      }
      
      if ($c eq ')') {
         # closes a nest
         $current_exp .= $c;
      
         if (!@nesttings) {
            carp "string '$string' has unmatched $c at position $i. (starting from 1)";
            return undef;
         }
      
         pop @nesttings;
      
         next;
      }

      if ($c eq $delimiter && !@nesttings) {
         # got a complete exp
      
         push @exps, $current_exp;
      
         $current_exp = ''; # reset $current_exp
      } else {
         $current_exp .= $c;
      }
   }
      
   push @exps, $current_exp;
      
   if ($quote_char) {
      carp "string '$string' has unmatched $quote_char at position $quote_pos. (starting from 1)";
      return undef;
   }
      
   if (@nesttings) {
      carp "string '$string' has unmatched '(', last one at position $nesttings[-1]. (starting from 1)";
      return undef;
   }
      
   return \@exps;
}
      
sub get_ExpHash_from_ArrayOfStrings {
   my ($ArrayOfStrings, $opt) = @_;
      
   my $ret;
      
   for my $string (@$ArrayOfStrings) {
      # CumQty=${14},Price=sprintf("%.2f",${44}),Open/Close=${77}
      
      my $pairs = get_exps_from_string($string, $opt);
      
      for my $p (@$pairs) {
         # Price=sprintf("%.2f",${44})
      
         if ($p =~ /^(.+?)=(.+)/) {
            my ($k, $v) = ($1, $2);
            $ret->{$k} = $v;
         } else {
            if ($opt->{SkipBadExp}) {
               carp "bad format at '$p'. expecting 'key=value'";
            } else {
               croak "bad format at '$p'. expecting 'key=value'";
            }
         }
      }
   }

   return $ret;
}
   
sub transpose_arrays {
    my ($arrays, $opt) = @_;
   
   $opt->{verbose} && print STDERR "transpose_arrays arrays = ", Dumper($arrays);
   
   my @out_array;
   
   return \@out_array if !$arrays;
   
   my $type = ref $arrays;
   
   $type = "" if ! $type;
   
   croak "wrong type='$type' when calling transpose_arrays" if !$type || $type ne 'ARRAY';
   
   my $num_arrays = scalar(@$arrays);
   
   my $max;
   
   my $i;
   
   for my $a (@$arrays) {
      $i++;
   
      my $count;
   
      if (!$a) {
         $count = 0;
      } else {
         my $type = ref $a;
   
         $type = "" if ! $type;
   
         croak "sub array ref $i wrong type='$type' when calling transpose_arrays"
            if !$type || $type ne 'ARRAY';
   
         $count = scalar(@$a);
      }
   
      if (!defined $max) {
         $max = $count;
      } else {
         if (!$opt->{TranposeLooseSize}) {
            croak "transpose_arrays input arrays have different sizes: $max vs $count"
               if $max != $count;
         } 

         if ($max < $count) {
            $max = $count;
         }
      }
   }
   
   return \@out_array if !$max;
   
   for (my $i=0; $i<$max; $i++) {
      my @a;

      for (my $j =0; $j<$num_arrays; $j++) {
         push @a, $arrays->[$j]->[$i];
      }
   
      push @out_array, \@a;
   }
   
   return \@out_array;
}
   
sub recursive_handle {
   my ($ref, $opt) = @_;
   
   # <?xml version="1.0"?>
   # <topology>
   #    <match name='A_B'/>
   #    <match name='C_D'/>
   #    <match name='E_F'/>
   # </topology>
   #
   # 1. before first call
   # $opt = {
   #    XMLpath  => '$root',   # default to '$root'
   #    XMLlevel => 0,         # default to 0
   #    XMLnodes => ['$root'], # default to [$path]
   #    XMLtypes => ['HASH'],  # default to let the called function to find
   # };
   # recursive_handle($ref, $opt);
   #
   # 2. before the second call
   # $opt = {
   #    XMLpath  => '$root->{match}',
   #    XMLlevel => 1,
   #    XMLnodes => ['$root', 'match'],
   #    XMLtypes => ['HASH', 'ARRAY'],
   # };
   # recursive_handle($ref, $opt);
   #
   # 3. before the 3rd call
   # $opt = {
   #    XMLpath => '$root->{match}->[0]',
   #    XMLlevel => 2,
   #    XMLnodes => ['$root', 'match', 0],
   #    XMLtypes => ['HASH', 'ARRAY', 'HASH'],
   # };
   # recursive_handle($ref, $opt);
   
   my ($path, $level, $nodes, $types) = @{$opt}{qw(XMLpath XMLlevel XMLnodes XMLtypes)};

   $path = '$root' if !defined $path;
   print "$path\n" if $opt->{verbose} || $opt->{RecursivePrint};
   
   $level = 0 if !defined $level;
   
   $nodes = [$path] if !defined $nodes;
   my $node = $nodes->[-1];
   
   my $type;
   
   if ($types) {
      $type = $types->[-1];
   } else {
      $type = ref $ref;
      $types = [ $type ];
   }
   
   $type = '' if ! $type;

   my $value = $type eq ''       ? $ref  :
               $type eq 'SCALAR' ? $ref  :
                                   undef ;
   
   my $r;
   
   @{$r}{qw(path   type   node   value  current   level   nodes   types)}
        = ($path, $type, $node, $value,    $ref, $level, $nodes, $types);
   
   if (    $opt->{Handlers}    && @{$opt->{Handlers}}
        || $opt->{FlowControl} && @{$opt->{FlowControl}} ) {

      TPSUP::Expression::export_var($r, {RESET=>1});
   
      if ($opt->{verbose}) {
         $TPSUP::Expression::verbose = 1;
      }
   }
   
   my $ret;
   $ret->{error} = 0;
   
   if ($opt->{Handlers}) {
      ROW:
      for my $row (@{$opt->{Handlers}}) {
         my ($match,      $action,
             $match_code, $action_code) = @$row;
      
         if ($match->()) {
            if ($opt->{verbose}) {
               print STDERR "matched: $match_code\n",
                            "action: $action_code\n";
            }
         } else {
            next ROW;
         }
      
         if (!$action->()) {
            print STDERR "ERROR: failed at path=$path\n";
      
            if ($opt->{verbose}) {
               print STDERR "r = ", Dumper($r);
      
               print STDERR "TPSUP::Expression vars =\n";
               TPSUP::Expression::dump_var();
            }
      
            $ret->{error} ++;
         }
      }
   }
      
   if ($opt->{FlowControl}) {
      for my $row (@{$opt->{FlowControl}}) {
         my ($match, $direction, $match_code, $direction_code) = @$row;
      
         if ($match->()) {
            if ($opt->{verbose}) {
               print STDERR "matched:   $match_code\n",
                            "direction: $direction_code\n";
            }
      
            if ($direction eq 'prune') {
               return $ret;
            } elsif ($direction eq 'exit') {
               $ret->{exit} ++;
               return $ret;
            } else {
               croak "unknown FlowControl driection='$direction'";
            }
         }
      }
   }
      
   if (!$type || $type eq 'SCALAR') {
      # end node

      return $ret;
   }
      
   $level ++;
      
   # RecursiveDepth is for flow control, violation means return to calling function
   my $max_depth = $opt->{RecursiveDepth};
      
   if ($max_depth && $level > $max_depth) {
      return $ret;
   }
      
   # RecursiveMax is for safety, violation means exit
   my $max_level = defined $opt->{RecursiveMax} ? $opt->{RecursiveMax} : 100;
      
   if ($level > $max_level) {
      croak "recursive level($level) > max_level($max_level), path=$path";
   }
      
   if ($type eq 'ARRAY') {
      my $i=0;
      
      for my $r (@$ref) {
         my $opt2;
         %$opt2 = %$opt;

         $opt2->{XMLlevel} = $level;
        
         $opt2->{XMLpath} = $path . "->[$i]";
      
         $opt2->{XMLnodes} = [@$nodes, $i];

         my $new_type = ref $r;
         $opt2->{XMLtypes} = [@$types, $new_type];
      
         $i++;
      
         $opt->{verbose} && print STDERR "entering $opt2->{XMLpath}, $opt2=", Dumper($opt2);
      
         my $ref = recursive_handle($r, $opt2);
      
         $ret->{error} += $ref->{error};
     
         if ($ref->{exit}) {
            $ret->{exit} ++;
            last;
         }
      }
      
      return $ret;
   } elsif ($type eq 'HASH') {
      for my $k (keys %$ref) {
         my $v = $ref->{$k};

         my $opt2;
         %$opt2 = %$opt;
      
         $opt2->{XMLlevel} = $level;
      
         $opt2->{XMLpath} = $path . "->{$k}";
      
         $opt2->{XMLnodes} = [@$nodes, $k];
      
         my $new_type = ref $v;
         $opt2->{XMLtypes} = [@$types, $new_type];
      
         $opt->{verbose} && print STDERR "entering $opt2->{XMLpath}, $opt2=", Dumper($opt2);
      
         my $ref = recursive_handle($v, $opt2);
      
         if ($ref->{exit}) {
            $ret->{exit} ++;
            last;
         }
      }

      return $ret;
   }
      
   croak "path=$path, cannot handle type=$type";
}
      
sub chkperl {
   my ($string, $opt) = @_;
      
   my $warn = $opt->{verbose} ? "use" : "no";
      
   my $compiled = eval "$warn warnings; no strict; sub { $string }";
      
   if ($@) {
      print STDERR "ERROR: $@, string='$string'\n";
      return 0;
   } elsif ($opt->{verbose}) {
      print STDERR "OK: compiled. string=$string\n";
      return 1;
   }
}
      
sub compile_perl {
   my ($string, $opt) = @_;
      
   my $ret;
      
   my $warn = $opt->{verbose} ? "use" : "no";

   my $compiled;

   $compiled = eval "$warn warnings; no strict; package TPSUP::Expression; sub { $string }";
   
   $ret->{error} = $@;
   $ret->{compiled} = $compiled;
   
   return $ret;
}
   
sub compile_perl_array {
   my ($in_array, $opt) = @_;
   
   my @out_array; # compiled code
   
   return undef if !$in_array;
   
   my $type = ref $in_array;
   $type = '' if !$type;
   
   croak "compile_perl_array() input wrong type='$type', expecting ARRAY"
      if !$type || $type ne 'ARRAY';
   
   for my $string (@$in_array) {
      my $ref = compile_perl($string, $opt);

      croak "$ref->{error}: $string" if $ref->{error};
   
      push @out_array, $ref->{compiled};
   }

   return \@out_array;
}
   
sub compile_paired_strings {
   my ($input, $opt) = @_;
   
   my @strings;
   
   my $type = ref $input;
   if (!$type) {
      @strings = ($input);
   } elsif ($type eq 'ARRAY') {
      @strings = @{$input};
   } else {
      croak "unsupported type='$type'. must be scalar or a ref to ARRAY, input = " . Dumper($input);
   }

   my $ret;
   
   for my $string (@strings) {
      # string:
      # 'CumQty=${14},Price=sprintf("%.2f",${44}),Open/Close=${77}'
      # break it into pairs
      # ('CumQty=${14}', 'Price=sprintf("%.2f",${44})', 'Open/Close=${77}')
      
      my $pairs = get_exps_from_string($string, $opt);
      for my $pair (@$pairs) {
         if ($pair =~ /^(.+?)=(.+)/) {
            my ($c, $e) = ($1, $2);
            push @{$ret->{Cols}}, $c;
      
            my $compiled = TPSUP::Expression::compile_exp($e, $opt);
      
            push @{$ret->{Exps}}, $compiled;
      
            $ret->{Hash}->{$c} = $compiled;
         } else {
            croak "bad Exp pair: '$pair'. Expecting 'key=exp'. from '$string'";
         }
      }
   }
      
   return $ret;
}
      
my $user_by_uid;
sub get_user_by_uid {
   my ($uid) = @_;
      
   if (! exists $user_by_uid->{$uid}) {
      # http://stackoverflow.com/questions/2899518/how-can-i-map-uids-to-user-names-using-perl-library-functions
      my @a = getpwuid($uid);
      $user_by_uid->{$uid} = $a[0];
   }
      
   return $user_by_uid->{$uid};
}
      
my $group_by_gid;
sub get_group_by_gid {
   my ($gid) = @_;

   if (! exists $group_by_gid->{$gid}) {
      # http://stackoverflow.com/questions/2899518/how-can-i-map-uids-to-user-names-using-perl-library-functions
      my @a = getgrgid($gid);
      $group_by_gid->{$gid} = $a[0];
   }
      
   return $group_by_gid->{$gid};
}
      
sub tpfind {
   my ($paths, $opt) = @_;
      
   my $opt2 = {%$opt};
      
   if (    $opt->{HandleExps} && @{$opt->{HandleExps}}
        && $opt->{HandleActs} && @{$opt->{HandleActs}} ) {

      my $exps = compile_perl_array($opt->{HandleExps});
      my $acts = compile_perl_array($opt->{HandleActs});
      
      $opt2->{Handlers} = transpose_arrays([$exps, $acts, $opt->{HandleExps}, $opt->{HandleActs}], $opt);
   }
      
   if (    $opt->{FlowExps} && @{$opt->{FlowExps}}
        && $opt->{FlowDirs} && @{$opt->{FlowDirs}} ) {
      
      my $exps = compile_perl_array($opt->{FlowExps});
      my $dirs = $opt->{FlowDirs} ;
      
      $opt2->{FlowControl} = transpose_arrays([$exps, $dirs, $opt->{FlowExps}, $opt->{FlowDirs}], $opt);
   }
      
   my $ret;
      
   for my $path (@$paths) {
      my $ref = recursive_path($path, 0, $opt2);
      
      $ret->{error} += $ref->{error};
   }
      
   return $ret;
}
      
sub recursive_path {
   my ($path, $level, $opt) = @_;
      
   my $ret;
   $ret->{error} = 0;
      
   if (! -e $path) {
      return $ret;
   }
      
   if ($opt->{RecursivePrint} || $opt->{verbose}) {
      print "$path\n";
   }
      
   my $type = (-f $path) ? 'file'    :
              (-d $path) ? 'dir'     :
              (-l $path) ? 'link'    :
                           'unknown' ;

   my ($dev, $ino, $mode, $nlink, $uid, $gid, $rdev, $size, $atime, $mtime, $ctime, $blksize, $blocks)
      = lstat($path);
   
   my $user = get_user_by_uid($uid);
   $user = $uid if ! $user;
   
   #print "user = $user\n";
   #print Dumper($user_by_uid);
   
   my $group = get_group_by_gid($gid);
   $group = $gid if ! $group;
   
   my $now=time();

   my $r;
   
   # mystery: for some reason, 'user' cannot be used in the expresssion. changed
   # to use 'owner' instead
   # @{$r}{qw(path type mode uid gid size mtime user group now)}
   #  = ($path, $type, $mode, $uid, $gid, $size, $mtime, $user, $group, $now);

   @{$r}{qw(path    type   mode   uid   gid   size   mtime   owner  group   now)}
         = ($path, $type, $mode, $uid, $gid, $size, $mtime, $user, $group, $now);
   
   #print "r=", Dumper($r);
   
   if (    $opt->{Handlers} && @{$opt->{Handlers}}
        || $opt->{FlowControl} && @{$opt->{FlowControl}} ) {

      TPSUP::Expression::export_var($r, {RESET=>1});
   
      #TPSUP::Expression::dump_var(); # I can see 'user' was populated even at this step

      if ($opt->{verbose}) {
         $TPSUP::Expression::verbose = 1;
      }
   }
   
   if ($opt->{Handlers}) {
      ROW:
      for my $row (@{$opt->{Handlers}}) {
         my ($match,      $action,
             $match_code, $action_code) = @$row;
   
            if ($match->()) {
               if ($opt->{verbose}) {
                  print STDERR "matched: $match_code\n",
                               "action:  $action_code\n";
               }
            } else {
               next ROW;
            } 

            if (! $action->()) {
               print STDERR "ERROR: failed at path=$path\n";

               $ret->{error} ++;
            }
         }
      }
      
      if ($opt->{FlowControl}) {
         for my $row (@{$opt->{FlowControl}}) {
            my ($match, $direction, $match_code, $direction_code) = @$row;
      
            if ($match->()) {
               if ($opt->{verbose}) {
                  print STDERR "matched:   $match_code\n",
                               "direction: $direction_code\n";
               }

               if ($direction eq 'prune') {
                  return $ret;
            } elsif ($direction eq 'exit') {
               $ret->{exit} ++;
               return $ret;
            } else {
               croak "unknown FlowControl driection='$direction'";
            }
         }
      }
   }
      
   if (-f $path) {
      # this is a file

   } elsif (-d $path) {
      # this is a dir
      
      $level ++;
      
      my $max_level = defined $opt->{RecursiveMax} ? $opt->{RecursiveMax} : 100;
      
      if ($level > $max_level) {
         if (defined $opt->{RecursiveMax}) {
            # this is user-defined limit - it is intentional, so return without complain
            return $ret;
         } else {
            # this is safety catch
            croak "recursive level($level) > max_level($max_level), path=$path";
         }
      }
      
      my $dfh;
      opendir($dfh, $path);
      
      if (!$dfh) {
         print STDERR "cannot open dir $path\n";
         $ret->{error} ++;
      } else {
         my @files_in_dir = readdir($dfh);
      
         for my $f (sort @files_in_dir) {
            next if $f eq '.' || $f eq '..';
      
            my $ref = recursive_path("$path/$f", $level, $opt);
      
            $ret->{error} += $ref->{error};
      
            if ($ref->{exit}) {
               $ret->{exit} ++;
               last;
            }
         }
      }
   } elsif (-l $path) {
      # this is a link
   } else {
      carp "unknown file type $path";
   }
      
   return $ret;
}
      
sub insert_namespace_code {
   my ($namespace, $code, $opt) = @_;
      
   eval "package $namespace; $code";
      
   if ($@) { 
      carp "namespace='$namespace' failed to load code='$code': $@";
      
      if ($opt->{SkipBadCode}) {
         return 0;
      } else {
         exit 1;
      }
   }
      
   return 1;
}
      
sub insert_namespace_file {
   my ($namespace, $file, $opt) = @_;
      
   my $code = `cat $file`;
           
   return insert_namespace_code($namespace, $code, $opt);
}
      
sub insert_namespaces {
   my ($ref, $type, $opt) = @_;
   my $error = 0;
      
   for my $pair (@$ref) {
      # TPSUP::FIX,TPSUP::CSV=/home/tian/tpsup/scripts/tpcsv2_test_codefile.pl
      
      if ($pair =~ /^(.+?)=(.+)/s) {
         my ($namespaces, $string) = ($1, $2);
      
         for my $ns (split /,/, $namespaces) {
            if ($type eq 'file') {
               insert_namespace_file($ns, $string, $opt) || $error ++;
            } elsif ($type eq 'code') {
               insert_namespace_code($ns, $string, $opt) || $error ++;
            } else {
               croak "unknowtype='$type' when calling insert_namespaces().";
            }
         }
      } else {
         croak "bad format at '$pair'; expecting 'namespace1,namespace2,...=string'";
      }
   }
      
   return 0 if $error;
      
   return 1;
}
      
sub unique_array {
   my ($in_arrays, $opt) = @_;

   #$in_arrays is a ref to array of arrays

   my @out_array;
   my $seen;
      
   for my $in_array (@$in_arrays) {
      for my $e (@$in_array) {
         next if $seen->{$e};

         push @out_array, $e;

         $seen->{$e} = 1;
      }
   }
      
   return \@out_array;
}

sub sort_unique {
   my ($in_arrays, $opt) = @_;

   #$in_arrays is a ref to array of arrays
      
   my $seen;
      
   for my $in_array (@$in_arrays) {
      for my $e (@$in_array) {
         $seen->{$e} ++;
      }
   }
      
   my @out_array;
    
   if ($opt->{SortUniqueNumeric}) {
      @out_array = sort {$a <=> $b} keys(%$seen);
   } else {
      @out_array = sort {$a cmp $b} keys(%$seen);
   }
      
   return \@out_array;
}
      
sub trim_path {
   my ($path, $opt) = @_;
      
   # /a/b/c/../d -> /a/b/d
      
   my $cwd = Cwd::abs_path();
      
   if ($path eq '.') {
      $path = $cwd;
   } elsif ($path =~ m:/^[.]/(.*):) {
      my $rest = $1;
      
      $path = "$cwd/$rest";
   } elsif ($path eq '..') {
      $path = "$cwd/..";
   } elsif ($path =- m:^[.][.]/(.*)$:) {
      my $rest = $1;
      
      $path = "$cwd/../$rest";
   }
      
   my @a1 = split /\/+/, $path;
   shift @a1; # shift away the undef before the first /
      
   my @a2;
      
   for my $e (@a1) {
      if ($e eq '.') {
         # convert /a/./b to /a/b
         next;
      } elsif ( $e eq '..' ) {
         # convert /a/b/../c to /a/c
         pop @a2;
         next;
      } else {
         push @a2, $e;
         next;
      }
   }
      
   my $newpath = '/' . join('/', @a2);
      
   return $newpath;
}
      
sub reduce_path {
   my ($old_path, $opt) = @_;
      
   # pathl::path2::path3:pathl:path2 -> pathl::path2::path3
      
   my @old = split /:/, $old_path;
      
   my $seen;
     
   my @new;
      
   my $i = 0;
      
   for my $p (@old) {
      if ($seen->{$p}) {
         print STDERR "dropping duplicate at $i: '$p'\n" if $opt->{verbose};
      } else {
         $seen->{$p}++;
         push @new, $p;
      }
      
      $i++;
   }
      
   my $new_path = join(":", @new);
      
   return $new_path;
}
      
sub get_java {
   my ($opt) = @_;
      
   my $result;

   my $java;
      
   if ($opt->{java}) {
      $java = $opt->{java};
      
      if (!-f $java) {
         $result->{error} = "$java not found";
         return $result;
      }
   } else {
      $java = "which java"; chomp $java;
      
      if (!$java) {
         my $other_familiar_places = [
            '/dir1/java/*/bin/java', '/dir2/java/*/bin/java',
         ];
      
         for my $pattern (@$other_familiar_places) {
            $java = `/bin/ls -1 $pattern|tail -1`;
      
            if ($java) {
               chomp $java;
               print STDERR "but found java=$java\n";
               last;
            }
         }
      
         if (!$java) {
            $result->{error} = "java not found";
            return $result;
         }
      }
   }
      
   $result->{java} = $java;
      
   my @lines = `$java -version 2>&1`; chomp @lines;
      
   # $ java -version
   # java version "1.6.0_22"
   # Java(TM) SE Runtime Environment (build 1.6.0_22-b04)
   # Java HotSpot(TM) 64-Bit Server VM (build 17.1-b03, mixed mode)

   # $ java -version
   # java version "1.5.0_85"
   # Java(TM) 2 Runtime Environment, Standard Edition (build 1.5.0_85-bll)
   # Java HotSpot(TM) Server VM (build 1.5.0_85-bll, mixed mode)
      
   my $version_main;
   my $version_long;
      
   for my $line (@lines) {
      if ($line =~ /java version "(.+?)"/) {
         $version_long = $1;

         if ($version_long =~ /^(\d+[.]\d+)/) {
            $version_main = $1;
         }

         last;
      }
   }
      
   if (!$version_main) {
      $result->{error} = "cannot fingure out java version from 'java -version' output:\n@lines";
      return $result;
   }
      
   $result->{version_main} = $version_main;
   $result->{version_long} = $version_long;
      
   return $result;
}
      
sub glob2regex {
   my ($glob, $opt) = @_;
      
   my $regex = $glob;
      
   $regex =~ s/[.]/\[.\]/g;
   $regex =~ s/[?]/./g;
   $regex =~ s/[*]/.*/g;
      
   return $regex;
}
      
###################################################################
package TPSUP::Expression;

no strict 'refs';
      
sub chkperl {
   my ($string, $opt) = @_;
      
   if ($opt->{Double2SingleQuote}) {
      $string =~ s/"/'/g; # use this test perl-like expression in cfm config
   }
      
   my $warn = $opt->{verbose} ? "use" : "no";
      
   my $compiled = eval "$warn warnings; no strict; sub { $string }";
      
   if ($@) {
      print STDERR "\nERROR: string='$string', $@\n";
      return 0;
   #} elsif ($opt->{verbose}) {
   } else {
      my $max = 50;

      my $substring;

      if ($TPSUP::Expression::verbose) {
         $substring = $string;
      } else {
         if (length($string) > $max) {
            $substring = substr($string, 0, $max);
            $substring .= "(truncated)";
         } else {
            $substring = $string;
         }
      }

      print STDERR "OK: compiled. string='$substring'\n";
      return 1;
   }
}

sub ifh {
   my ($path, $opt) = @_;

   return TPSUP::UTIL::get_in_fh($path, $opt);
}

sub ofh {
   my ($path, $opt) = @_;

   return TPSUP::UTIL::get_out_fh($path, $opt);
}

1
  
