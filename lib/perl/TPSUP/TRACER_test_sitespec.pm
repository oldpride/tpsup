package TPSUP::TRACER_test_sitespec;

use warnings;
use strict;
use Carp;
use Data::Dumper;
use TPSUP::SQL qw(run_sql);

use base qw( Exporter );
our @EXPORT_OK = qw(
   update_security_knowledge
   get_sids_by_security
   get_security_by_sid
);

my $sids_by_security;
sub get_sids_by_security {
   my ($security, $opt) = @_;

   my $verbose = $opt->{verbose};

   return $sids_by_security->{$security} if exists $sids_by_security->{$security};

   my $Sid_clause = "";
   if ($security =~ /^\d+$/) {
      # if this is a number, then it could also be a SID
      $Sid_clause = "or Sid  = '$security'";
   }

   my $type_clause = "
            ( Symbol = '$security' or Cusip = '$security' 
             or Isin = '$security' or Sedol = '$security'
             $Sid_clause
            )";
   if (defined($opt->{SecType}) && $opt->{SecType} !~ /SECURITY/i) {
      $type_clause = "$opt->{SecType} = '$security'";
   } 
   
   my $db = 'tptest@tpdbmssql';
   my $sql = "
      select sid from securities (nolock)
      where IsActive = 'Y'
            and $type_clause
   ";

   my $opt2 = {};
   if ($verbose) {
      $opt2 = { 
         out_fh => \*STDERR, 
         RenderOutput => 1,
         verbose => $verbose,
         # MaxColumnWidth => $entity_cfg->{MaxColumnWidth},
      };

      print qq(sql $db "$sql"\n);
   }


   my $result = run_sql($sql, {nickname=>$db,
                               ReturnDetail => 1,
                               %$opt2,
                              }
                        );

   croak "failed to run sql=$sql" if !$result;
   $sids_by_security->{$security} = [];

   for my $row (@{$result->{aref}}) {
      push @{$sids_by_security->{$security}}, $row->[0];   
   }
                        
   return $sids_by_security->{$security};
}

my $security_by_sid_type;
sub get_security_by_sid {
   my ($sid, $opt) = @_;

   return $security_by_sid_type->{$sid} if exists $security_by_sid_type->{$sid};

   my $db = 'tptest@tpdbmssql';
   my $sql = "
      select * from securities (nolock)
      where sid = '$sid'
            and IsActive = 'Y'
   ";

   my $result = run_sql($sql, {nickname=>$db,
                               # output => '-',
                               # RenderOutput => 1,
                               ReturnDetail => 1,
                               # MaxColumnWidth => $entity_cfg->{MaxColumnWidth},
                              }
                        );

   croak "failed to run sql=$sql" if !$result;

   croak "Sid is not unique, matched multiple ", Dumper($result->{aref})
      if @{$result->{aref}} >1;

   if (@{$result->{aref}} == 0 ) {
      $security_by_sid_type->{$sid} = {};
   } else { 
      my $r;
      @{$r}{@{$result->{headers}}} = @{$result->{aref}->[0]};
      $security_by_sid_type->{$sid} = $r;
   }
                        
   return $security_by_sid_type->{$sid};
}


my $has_updated_security_knowledge;
sub update_security_knowledge {
   my ($known, $key, $opt) = @_;

   return if $has_updated_security_knowledge;

   $has_updated_security_knowledge++;

   print "extending knowledge about security from $key=$known->{$key}\n";

   my $sids = get_sids_by_security($known->{$key}, {
                                                    SecType=>$key, 
                                                    output=>'-',
                                                    RenderOutput=>1,
                                                    verbose=>$opt->{verbose},
                                                   }
                                  );

   if (!@$sids) {
      croak "cannot match $key=$known->{$key} to a Sid"; 
   } elsif (@$sids >1) {
      croak "$key=$known->{$key} matched to multiple Sids"; 
   } 
      
   my $sid = $sids->[0];

   my $sec_by_type = get_security_by_sid($sid);

   for my $type (sort (keys %$sec_by_type)) {
      my $value = $sec_by_type->{$type};
      next if ! defined $value;

      $known->{uc($type)} = $value;
   }

   return $known;  
   # we don't have return anything. this returned value is for test's convenience
}

sub main {
   for my $cmd (( 
        "get_sids_by_security('IBM', {verbose=>1})",
        "get_security_by_sid(40000, {verbose=>1})",
        "update_security_knowledge( {BOOKID=>3000001, SID=>'40000'}, 'SID', {verbose=>1})",
      )) {

      print "----------------------------------------------------------------------\n";
      my $result;
      eval "\$result = $cmd";
      croak "$@" if $@;
      print "$cmd = ", Dumper($result);
   }
}

main() unless caller();


1
