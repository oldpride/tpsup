package TPSUP::SFTP;

use strict;
use base qw( Exporter );
our @EXPORT_OK = qw(
  parse_sftp_url
  parse_user_password
  parse_host_port_path
  test_sftp_url
);

use Carp;
use Data::Dumper;
$Data::Dumper::Sortkeys = 1;    # this sorts the Dumper output!
$Data::Dumper::Terse    = 1;    # print without "$VAR1="
use TPSUP::UTIL qw(get_timestamp parse_rc get_abs_path get_user);
use TPSUP::TMP  qw(get_tmp_file);
use TPSUP::SSH  qw(get_ssh_opt);

sub parse_sftp_url {
   my ( $url, $opt ) = @_;

   my $protocol;
   my $text;
   my $user;
   my $encoded_password;
   my $decoded_password;
   my $host;
   my $port;
   my $path;

   # examples:
   # sftp://user:password@host:port/path

   if ( $url =~ m|^(.+?)://(.+)| ) {
      # sftp://user:password@host:port/path

      $protocol = $1;
      $text     = $2;
   } else {
      # user:password@host:port/path

      $protocol = 'sftp';
      $text     = $url;
   }

   if ( $text =~ m|^(.+?)@(.+)| ) {
      # user:password@host:port/path

      my $user_password  = $1;
      my $host_port_path = $2;

      ( $user, $encoded_password, $decoded_password ) = parse_user_password( $user_password, $opt );

      ( $host, $port, $path ) = parse_host_port_path( $host_port_path, $opt );
   } else {
      # host:port/path

      $user             = get_user();
      $encoded_password = '';
      $decoded_password = '';

      ( $host, $port, $path ) = parse_host_port_path( $text, $opt );

   }

   my $ret;
   @{$ret}{qw(user encoded_password decoded_password host port path)} =
     ( $user, $encoded_password, $decoded_password, $host, $port, $path );

   return $ret;
}

sub parse_user_password {
   my ( $user_password, $opt ) = @_;

   my $user;
   my $encoded_password;
   my $decoded_password;

   my $func = $opt->{decode_func};

   if ( $user_password =~ m|^(.+?):(.+)$| ) {
      # example: user:password
      $user             = $1;
      $encoded_password = $2;
   } else {
      # example: user
      $user             = $user_password;
      $encoded_password = '';
   }

   if ($func) {
      $decoded_password = $func->($encoded_password);
   } else {
      $decoded_password = $encoded_password;
   }

   return ( $user, $encoded_password, $decoded_password );
}

sub parse_host_port_path {
   my ( $host_port_path, $opt ) = @_;

   my $host;
   my $port;
   my $path;

   if ( $host_port_path =~ m|^(.+?):(.+?)/(.+)$| ) {
      # example: host:port/path
      $host = $1;
      $port = $2;
      $path = $3;
   } elsif ( $host_port_path =~ m|^(.+?)/(.+)$| ) {
      # example: host/path
      $host = $1;
      $port = 22;
      $path = $2;
   } elsif ( $host_port_path =~ m|^(.+?):(.+)$| ) {
      # example: host:port
      $host = $1;
      $port = $2;
      $path = '';
   } else {
      # example: host

      $host = $host_port_path;
      $port = 22;
      $path = '';
   }

   return ( $host, $port, $path );
}

sub test_sftp_url {
   my ( $url, $opt ) = @_;

   my $parsed = parse_sftp_url($url);

   my ( $user, $password, $decoded_password, $host, $port, $path ) =
     @{$parsed}{qw(user encoded_password decoded_password host port path)};

   my $ssh_opt = get_ssh_opt($opt);

   my $cmd;
   if ($decoded_password) {
      $cmd = "sftp $ssh_opt -P $port $user:$decoded_password\@$host";
   } else {
      $cmd = "sftp $ssh_opt -P $port $user\@$host";
   }

   print "cmd=$cmd\n" if $opt->{debug};

   open my $fh, "| $cmd" or croak "can't run $cmd: $!";

   sleep 1;

   if ( !$opt->{skip_password} ) {
      if ( !$password ) {
         print "please enter password: \n";
         my $password = <STDIN>;
         chomp $password;
         print $fh "$password\n";
      } else {
         print $fh "$password\n";
      }
      sleep 1;
   }

   $cmd = "cd $path";
   print "$cmd\n";
   print $fh "$cmd\n";
   sleep 1;

   $cmd = "ls";
   print "$cmd\n";
   print $fh "$cmd\n";
   sleep 1;

   $cmd = "exit";
   print "$cmd\n";
   print $fh "$cmd\n";
   sleep 1;

   close $fh;
}

sub main {
   require TPSUP::TEST;

   my $test_code = <<'END';
      TPSUP::SFTP::parse_sftp_url('sftp://livingstonchinese.org');
      TPSUP::SFTP::parse_sftp_url('sftp://livin80@livingstonchinese.org');
      TPSUP::SFTP::parse_sftp_url('sftp://livin80:123@livingstonchinese.org', {decode_func => sub { return int($_[0])+1; }});


      TPSUP::SFTP::test_sftp_url('sftp://livin80@livingstonchinese.org', {skip_password=>1});

END

   TPSUP::TEST::test_lines($test_code);

}

main() unless caller();

1;

