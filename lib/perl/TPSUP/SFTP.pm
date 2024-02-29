#!/usr/bin/env perl
package TPSUP::SFTP;

use strict;
use base qw( Exporter );
our @EXPORT_OK = qw(
  get_ssh_opt
);

use Carp;
use Data::Dumper;
$Data::Dumper::Sortkeys = 1;    # this sorts the Dumper output!
$Data::Dumper::Terse    = 1;    # print without "$VAR1="
use TPSUP::UTIL qw(get_timestamp parse_rc get_abs_path);
use TPSUP::TMP  qw(get_tmp_file);

sub get_ssh_opt {
   my ($opt) = @_;

   # return "-o StrictHostKeyChecking=no -o ConnectTimeout=5 -o BatchMode=yes";
   return "-o StrictHostKeyChecking=no -o ConnectTimeout=5";
}

sub parse_sftp_url {
   my ($url) = @_;

   my $user;
   my $password;
   my $host;
   my $port;
   my $path;

   if ( $url =~ m{^sftp://([^:]+):([^@]+)@([^:]+):(\d+)(/.*)$} ) {
      # with port
      $user     = $1;
      $password = $2;
      $host     = $3;
      $port     = $4;
      $path     = $5;
   } elsif ( $url =~ m{^sftp://([^:]+):([^@]+)@([^/]+)(/.*)$} ) {
      # without port
      $user     = $1;
      $password = $2;
      $host     = $3;
      $port     = 22;
      $path     = $4;
   } elsif ( $url =~ m{^sftp://([^@]+)@([^:]+):(\d+)(/.*)$} ) {
      # without password
      $user     = $1;
      $password = '';
      $host     = $2;
      $port     = $3;
      $path     = $4;
   } elsif ( $url =~ m{^sftp://([^@]+)@([^/]+)(/.*)$} ) {
      # without password and port
      $user     = $1;
      $password = '';
      $host     = $2;
      $port     = 22;
      $path     = $3;
   } else {
      croak "can't parse sftp url: $url";
   }

   return ( $user, $password, $host, $port, $path );
}

sub decode_password {
   my ( $password, $opt ) = @_;

   my $func = $opt->{decode_func};

   if ($func) {
      return $func->($password);
   } else {
      return $password;
   }
}

sub test_sftp_url {
   my ( $url, $opt ) = @_;

   my ( $user, $password, $host, $port, $path ) = parse_sftp_url($url);

   $password = decode_password( $password, $opt );

   my $ssh_opt = get_ssh_opt($opt);

   my $cmd;
   if ($password) {
      $cmd = "sftp $ssh_opt -P $port $user:$password\@$host";
   } else {
      $cmd = "sftp $ssh_opt -P $port $user\@$host";
   }

   print "cmd=$cmd\n" if $opt->{debug};

   open my $fh, "| $cmd" or croak "can't run $cmd: $!";

   sleep 1;

   if ( !$password ) {
      print "please enter password: \n";
      my $password = <STDIN>;
      chomp $password;
      print $fh "$password\n";
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
   my $url = "livin80_ftp @livingstonchinese.org";

   my $opt = {};

   test_sftp_url( $url, $opt );
}
1;

