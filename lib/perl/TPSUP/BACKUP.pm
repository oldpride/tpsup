#!/usr/bin/env perl

package TPSUP::BACKUP;

use strict;
use Carp;
use base qw( Exporter );
our @EXPORT_OK = qw(
   resolve_vars
);

my $home = `/bin/bash -c "echo ~"`;
chomp $home;

my $today = `date +%Y%m%d`;
chomp $today;

# set user, appdata from environment variables. we will validate them when we actually use them.
my $user = $ENV{USERNAME};
my $appdata = $ENV{APPDATA};
# change C:\Users\tian\AppData\Roaming to C:/Users/tian/AppData/Roaming
$appdata =~ s:\\:/:g;

my $default_dict = {
   home    => $home,
   user    => $user,
   appdata => $appdata,
   today   => $today,
}; 

sub resolve_vars {
   my ($str, $dict2) = @_;

   my $dict3;
   if (!defined $dict2) {
      $dict3 = $default_dict;
   } else {
      $dict3 = { %$default_dict, %$dict2 };
   }
   
   for my $k (sort (keys %$dict3)) {
      my $v = $dict3->{$k};

      if (defined $v) {
         $str =~ s:\$$k:$v:g;
      } else {
         croak "var=$k is not defined in string=$str";
      }
   }
   return $str;
}

1
