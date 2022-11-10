package TPSUP::SHELL;

use strict;
use base qw( Exporter );
our @EXPORT_OK = qw(
   parse_string_like_shell
   run_bash
   parse_bash_cfg_string
   parse_bash_cfg_file
);


use Carp;
$SIG{ __DIE__ } = \&Carp::confess; # this stack-trace on all fatal error !!!

use Data::Dumper;
$Data::Dumper::Terse = 1;     # print without "$VAR1="
$Data::Dumper::Sortkeys = 1;  # this sorts the Dumper output!

use TPSUP::UTIL qw(
   get_in_fh
   close_in_fh
   get_out_fh
   close_out_fh
   get_tmp_file
);

sub parse_string_like_shell {
   my ($string, $opt) = @_;

   my $file = __FILE__;

   my $cmd = "perl $file -dump $string";
   my $output;

   if (!$opt->{SHELL} || $opt->{SHELL} eq 'bash') {
      # SHELL.pm default shell is bash; Perl default shell is sh
      # use bash shell

      my $result = run_bash($cmd);  
      $output = $result->{output};
      
      # ideally we should use Capture::Tiny module which is used frequently by perl installers
      # but Capture::Tiny is not part of core, therefore, we cannot use 
      #    use Capture::Tiny qw(capture);
      # because it fail at compile time.
      # we would have to use
      #   require Capture::Tiny;
      #   Capture::Tiny->import(qw(capture));
      # but this will tigger error
      #   Can't use string ("0") as a subroutine ref while "strict refs" in use at /usr/local/share/perl/5.26.1/Capture/Tiny.pm line 382
      # therefore, i gave up using Capture::Tiny for now.
      #   my ($error_output, $exit_code) = Capture::Tiny::capture {
      #      system('bash', '-c', $cmd);
      #   };
      #   confess "string is not parsable in shell: $string. cmd=$cmd" if $exit_code;
   } elsif ($opt->{SHELL} eq 'sh')  {
      $output = `$cmd`;             # this is sh, not bash
      confess "string is not parsable in shell: $string. cmd=$cmd" if $?;
   } else {
      confess "unsupported SHELL=$opt->{SHELL}";
   }

   my $ARGS;
   eval $output;
   if ($@) {
      confess "ERROR in parsing $output: $@\n";
   }

   return $ARGS;
}

sub run_bash {
   my ($cmd, $opt) = @_;

   # use "-"  so that we can put command into an array afterwards.
   # open my $ifh, "-|", "bash", "-c", $cmd;
   my @cmd_array = ("bash", "-c", $cmd);
   open my $ifh, "-|", @cmd_array;

   my $rc = $?;

   if ($rc) {
      die "cannot open file handler: rc=$rc $!"  . 
          "\ncmd_array = " . Dumper(\@cmd_array); 
   }


   my $output = "";

   while (<$ifh>) {
      $output .= $_; 
   }

   close $ifh;

   return { output=>$output, rc=>$rc};
}


sub parse_bash_cfg_file {
   my ($file, $opt) = @_;

   my $ifh = get_in_fh($file);
   my @lines = <$ifh>;
   my $string = join("", @lines);
   return parse_bash_cfg_string($string, $opt);
}


sub parse_bash_cfg_string {
   my ($string, $opt) = @_;

   my $verbose = $opt->{verbose};

   # parse a cfg file in bash synatx

   my $marker_line = "----- begin env -----";

   my $tmpfile = get_tmp_file("/var/tmp", "bash_cfg");
   $verbose && print "tmpfile = $tmpfile\n";

   my $ofh = get_out_fh($tmpfile);

   print {$ofh} <<"END";
#!/bin/bash


# export all vars
# without this, somehow 'env' will not display the newly-set env vars
set -a

$string

echo $marker_line
env # print out env

END

   close_out_fh($ofh);

   my $cmd = "chmod 755 $tmpfile";
   $verbose && print "cmd = $cmd\n";
   system($cmd);
   if ($? != 0) {
      croak "cmd=$cmd failed";
   }

   if ($opt->{ClearEnv}) {
      # https://stackoverflow.com/questions/9671027/sanitize-environment-with-command-or-bash-script
      $cmd = qq(env -i '$tmpfile');
   } else {
      $cmd = qq(env '$tmpfile');
   }

   $verbose && print "cmd = $cmd\n";

   open my $ifh, "$cmd|" or die "cannot read from cmd=$cmd: $!";

   my $output = "";
   while (<$ifh>) {
      $output .= $_;
   }
   
   close $ifh;

   $verbose && print "output = $output\n";

   $output =~ s/^.*?$marker_line//s;

   my $ret;

   for my $l (split (/\n/, $output)) {
      next if $l =~ /^\s*$/;

      if ($l =~ /^(.+?)=(.*)/) {
         # TODO: multi-line match doesn't work
         $ret->{$1} = $2;      
      } else {
         $verbose && print STDERR "line=$l is not in key=value format\n";
      }
   }

   return $ret;
}


sub main {
   if (@ARGV && $ARGV[0] eq '-dump') { 
      shift @ARGV;
      print '$ARGS =', Dumper(\@ARGV);
      exit 0;
   } 

   print "--------------------------------------------\n";
   {
      my @strings = (
         <<'END',
         a=1 b="has spaces" c='also has spaces' d=$HOME e=`date +%H:%M:%S` f="a'b" g=`[[ "abcde" =~ bcd ]] && echo matched` h=`i=1; ((i++)); echo $i`
END
      );
   
      print "test parse_string_like_shell() using sh. g/h will fail.\n";
      for my $s (@strings) {
         print "parse_string_like_shell($s) = ", Dumper(parse_string_like_shell($s, {SHELL=>'sh'}));
      }

      print "test parse_string_like_shell() using bash\n";
      for my $s (@strings) {
         print "parse_string_like_shell($s) = ", Dumper(parse_string_like_shell($s, {ClearEnv=>1}));
      }
   }

   print "--------------------------------------------\n";
   {
      print "test run_bash()\n";

      my @strings = (
         qq(echo "a'b"),
         'echo $BASH_VERSION',
         '[[ "abcde" =~ bcd ]] && echo matched',
         'i=1; ((i++)); echo $i',
         'echo `date "+%Y%m%d"`',
      );

      for my $s (@strings) {
         print "run_bash($s) = ", run_bash($s)->{output}, "\n";
      }
   }

   print "--------------------------------------------\n";
   {
      print "test parse_bash_cfg()\n";

      my @strings = (
         <<'END',
a=1 
b="has spaces" 
c='also has spaces' 
d=$HOME 
e=`date +%H:%M:%S` 
f="a'b" 
g=`[[ "abcde" =~ bcd ]] && echo matched` 
h=`i=1; ((i++)); echo $i`
i="multiline1
multiline2
           "
END
      );

      for my $s (@strings) {
         print "parse_bash_cfg_string($s) = ", Dumper(parse_bash_cfg_string($s, {ClearEnv=>1, verbose=>0})), "\n";
         my $tmpfile = get_tmp_file("/var/tmp", "test_bash_cfg");
         my $ofh = get_out_fh($tmpfile);
         print {$ofh} $s;
         close_out_fh($ofh);
         print "parse_bash_cfg_file($tmpfile) = ", Dumper(parse_bash_cfg_file($tmpfile, {ClearEnv=>1, verbose=>0})), "\n";
      }
   }
}

main() unless caller();

1
