package TPSUP::CHECK;

use strict;
use warnings;

use base qw( Exporter );
our @EXPORT_OK = qw(
  chkcmd
);

use Carp;

#use DBI;
use Data::Dumper;
use TPSUP::TMP  qw(get_tmp_file);
use TPSUP::UTIL qw(get_user);
use TPSUP::DATE qw(get_interval_seconds);

sub chkcmd {
   my ( $check, $opt ) = @_;

   # TODO: better format of time, maybe "day HH:MM" combination
   # TODO: better status report: maybe to indicate wether the test run
   # at all in a separate field

   my $ret;

   if ( !defined $check->{command} ) {
      $ret->{stauts} = "ERROR: command is not defined";
      return $ret;
   }

   my $has_something_to_expect;

   # TODO: make ExpectedRC an expression
   for my $attr (
      qw( ExpectedStdout   ExpectedStderr
      UnexpectedStdout UnexpectedStderr
      ExpectedRC       UnexpectedRC
      )
     )
   {
      if ( defined $check->{$attr} ) {
         $has_something_to_expect++;
         last;
      }
   }

   if ( !$has_something_to_expect ) {
      $ret->{stauts} = "ERROR: missing expectation";
      return $ret;
   }

   my ( $sec, $min, $hour, $mday, $mon, $year, $wday, $yday, $isdst ) =
     localtime(time);

   my $stamp = sprintf( "%4d%02d%02d-%02d%02d%02d",
      $year, $mon + 1, $mday, $hour, $min, $sec );

   $opt->{verbose} && print STDERR "$stamp\n";

   if ( defined $check->{day_of_week} ) {
      my @wdays = split /,/, $check->{day_of_week};

      if ( !grep { $wday eq $_ } @wdays ) {
         $ret->{stauts} =
"OK: NOT_IN_TIME_RANGE: day_of_week=$check->{day_of_week}, today=$wday";
         return $ret;
      }
   }

   if ( defined $check->{days} ) {

      #0101,0201,0301,...
      my @days = split /,/, $check->{days};

      #mmdd

      my $day = sprintf( "%02d%02d", $mon + 1, $mday );

      if ( !grep { "$day" eq $_ } @days ) {
         $ret->{stauts} = "OK: NOT_IN_DAYS: days=$check->{days}, today=$day";
         return $ret;
      }
   }

   if ( defined $check->{exclude_days} ) {

      #0101,0201,0301,...
      my @exclude_days = split /,/, $check->{exclude_days};

      #mmdd
      my $day = sprintf( "%02d%02d", $mon + 1, $mday );

      if ( grep { "$day" eq $_ } @exclude_days ) {
         $ret->{stauts} =
"OK: IN_E:gCLUDE_DAYS: exclude_days=$check->{exclude_days}, today=$day";
         return $ret;
      }
   }

   if ( defined $check->{time_ranges} ) {

      # time: 11:30-12:00,15:30-16:00

      my $HHMM_now = sprintf( "%0d:%0d", $hour, $min );

      my $is_in_range;

      for my $pair ( split /,/, $check->{time_ranges} ) {

         # 11:30-12:00

         if ( $pair =~ /^(\d{2}:\d{2})-(\d{2}:\d{2})$/ ) {
            my $HHMM_begin = $1;
            my $HHMM_end   = $2;

            if ( $HHMM_begin le $HHMM_now && $HHMM_now le $HHMM_end ) {
               $is_in_range++;

               last;
            }
         } else {
            $ret->{stauts} =
"ERROR: BAD_TIME_FORMAT in time_ranges at '$pair'. expecting HH:MM-HH:MM";
            return $ret;
         }
      }

      if ( !$is_in_range ) {
         $ret->{stauts} =
"OK: NOT_IN_TIME_RANGE: time_ranges=$check->{time_ranges}, now=$HHMM_now";
         return $ret;
      }
   }

   if ( defined $check->{users} ) {
      my @users = split /,/, $check->{users};

      my $user = get_user();

      if ( !grep { $user eq $_ } @users ) {
         $ret->{stauts} = "OK: NOT_IN_USERS: userss=$check->{users}, me=$user";
         return $ret;
      }
   }

   if ( defined $check->{hostnames} ) {
      my @hostnames = split /,/, $check->{hostnames};

      my $hostname = `hostname`;
      chomp $hostname;

      if ( !grep { $hostname eq $_ } @hostnames ) {
         $ret->{stauts} =
"OK: NOT_IN_HOSTNAMES: hostnames=$check->{hostnames}, localhost=$hostname";
         return $ret;
      }
   }
   my $tmpref;
   $tmpref->{Stdout} = get_tmp_file( "/var/tmp", "chk_stdout" );
   $tmpref->{Stderr} = get_tmp_file( "/var/tmp", "chk_stderr" );

   my $command = "$check->{command} >$tmpref->{Stdout} 2>$tmpref->{Stderr}";

   if ( defined $check->{timeout} ) {
      $command = "timedexec $check->{timeout} -- $command";
   }

   $opt->{verbose} && print STDERR "$command\n";

   my $before_YYYYMMDD =
     sprintf( "%04d%02d%02d", $year + 1900, $mon + 1, $mday );
   my $before_HHMMSS = sprintf( "%02d%02d%02d", $hour, $min, $sec );

   System($command);

   my $perl_rc = $?;

   my $sig = $perl_rc & 127;

   # $sig, ($? & 128)          ? 'CORED !!!' :
   # ($sig == 6 || $sig == 11) ? 'coredump disabled'
   #                             'no coredump' ;

   my $rc = $perl_rc & 0xffff;
   $rc >>= 8;

   ( $sec, $min, $hour, $mday, $mon, $year, $wday, $yday, $isdst ) =
     localtime(time);

   my $after_YYYYMMDD =
     sprintf( "%04d%02d%02d", $year + 1900, $mon + 1, $mday );
   my $after_HHMMSS = sprintf( "%02d%02d%02d", $hour, $min, $sec );

   $ret->{duration} = get_interval_seconds( $before_YYYYMMDD, $before_HHMMSS,
      $after_YYYYMMDD, $after_HHMMSS );

   $ret->{before} = "$before_YYYYMMDD $before_HHMMSS";
   $ret->{after}  = "$after_YYYYMMDD  $after_HHMMSS";

   my $maxchar = defined $opt->{maxchar} ? $opt->{maxchar} : 500;

   my $match;

   for my $venue (qw(Stdout Stderr)) {
      $ret->{output}->{$venue} = $tmpref->{$venue};

      if ( defined $check->{"Expected$venue"} ) {
         for my $pattern ( @{ $check->{"Expected$venue"} } ) {
            my @matches =
              grep { /$check->{"Expected$venue"}/ } $tmpref->{$venue};

            if (@matches) {
               $match->{"Expected$venue"}->{match} =
                 truncate_lines( $maxchar, \@matches );
               $match->{"Expected$venue"}->{ok} =
                 "matched /" . $check->{"Expected$venue"} . "/";
            } else {
               $match->{"Expected$venue"}->{error} =
                 "didn't match /" . $check->{"Expected$venue"} . "/";
            }
         }
      }

      if ( defined $check->{"Unexpected$venue"} ) {
         for my $pattern ( @{ $check->{"Unexpected$venue"} } ) {
            my @matches =
              grep { /$check->{"Unexpected$venue"}/ } $tmpref->{$venue};

            if (@matches) {
               $match->{"Unexpected$venue"}->{match} =
                 truncate_lines( $maxchar, \@matches );
               $match->{"Unexpected$venue"}->{error} =
                 "matched /" . $check->{"Unexpected$venue"} . "/";
            } else {
               $match->{"Unexpected$venue"}->{ok} =
                 "didn't match /" . $check->{"Unexpected$venue"} . "/";
            }
         }
      }
   }

   if ( defined $check->{ExpectedRC} ) {
      if ( "$rc" =~ /$check->{ExpectedRC}/ )
      {    # TODO: use eval to implement expression instead
         $match->{ExpectedRC}->{match} = ["$rc"];
         $match->{ExpectedRC}->{ok}    = "'$rc' matched /$check->{ExpectedRC}/";
      } else {
         $match->{ExpectedRC}->{error} =
           "'$rc' didn't match /$check->{ExpectedRC}/";
      }
   }

   if ( defined $check->{UnexpectedRC} ) {
      if ( "$rc" !~ /$check->{UnexpectedRC}/ ) {
         $match->{UnexpectedRC}->{match} = ["$rc"];
         $match->{UnexpectedRC}->{ok} =
           "'$rc' didn't match /$check->{ExpectedRC}/";
      } else {
         $match->{UnexpectedRC}->{error} =
           "'$rc' matched /$check->{UnexpectedRC}/";
      }
   }

   $ret->{match}  = $match;
   $ret->{status} = 'OK: DONE';

   return $ret;
}

sub truncate_lines {
   my ( $maxchar, $aref ) = @_;

   return $aref if !$maxchar;

   my $total_length = 0;

   my @truncated;

   for my $line (@$aref) {
      my $len = length($line);

      if ( $total_length + $len < $maxchar ) {
         push @truncated, $line;
         $total_length += $len;
         next;
      } else {
         push @truncated,
           substr( $line, 0, $maxchar - $total_length ) . "(truncated)";
         last;
      }
   }

   return \@truncated;
}
1
