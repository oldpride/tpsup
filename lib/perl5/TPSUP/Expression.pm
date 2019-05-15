package TPSUP::Expression;

use strict;
no strict "refs";
no strict "vars";

sub export {
   while (@_) {
      my ($k, $v) = splice(@_, 0, 2);
      next unless defined $k;
      ${k} = $v;
   }
}

my %_exist;

sub export_var {
   my ($ref, $opt) = @_;

   my $prefix = defined($opt->{ExpPrefix}) ? $opt->{ExpPrefix} :
                defined($Prefix)           ? $Prefix           :
		                             undef             ;

   if ($opt->{RESET} || $RESET) {
      if ($prefix) {
	 for my $k (keys %{${$prefix}}) {
	    if ( $opt->{Hash} ) {
	       for my $k2 (keys %{${$prefix}{$k}}) {
		  delete ${$prefix}{$k}{$k2};
	       }
	    }
	    undef ${$prefix}{$k};
	    delete ${$prefix}{$k};
	 }
      } elsif ($opt->{$FIX} || $FIX) {
	 %fix = ();
      } else {
	 for my $k (keys %_exist) {
            if ($opt->{Hash}) {
	       for my $k2 (keys %{$k}) {
		  delete ${$k}{$k2};
	       }
	    }

	    undef ${$k};
         }

	 %_exist = ();
      }
   }

   if ($prefix) {
      for my $k (keys %$ref) {
	 if ($opt->{Hash}) {
            for my $k2 (keys %${ref->{$k}}}) {
	       ${$prefix}{$k}{$k2} = $ref->{$k}->{$k2};
	    }
	 } else {
            ${$prefix}{$k} = $ref->{$k};
	 }
      }
   } elsif ($opt->{FIX}||$FIX) {
      for my $k (keys %$ref) {
         if ($opt->{Hash}) {
            for my $k2 (keys %${ref->{$k}}}) {
               $fix{$k}{$k2} = $ref->{$k}->{$k2};
            }
         } else {
            $fix{$k} = $ref->{$k};
         }
      }
   } else {
      for my $k (keys %$ref) {
         if ($opt->{Hash}) {
            for my $k2 (keys %${ref->{$k}}}) {
               ${$k}{$k2} = $ref->{$k}->{$k2};
	       $_exist{$k} = 1;
            }
         } else {
            ${$k} = $ref->{$k};
	    $_exist{$k} = 1;
         }
      }
   }
}

sub dump_var {
   my ($opt) = @_;

   my $DumpFH = defined($opt->{DumpFH}) ? $opt->{DumpFH} : \*STDERR;
   
   if ($opt->{FIX} || $FIX) {
      print {$DumpFH} "\$fix = \n";

      for my $k (sort {$a<=>$b} (keys %fix)) {
         if ($opt->{Hash}) {
            for my $k2 (sort keys(%{$fix{$k}}) ) {
               printf {$DumpFH} "%30s => %s\n", "\$fix{$k}{$k2}", "$fix{$k}{$k2}";
            }
         } else {
            printf {$DumpFH} "%30s => %s\n", "\$fix{$k}", "$fix{$k}";
         }
      }
   } else {
      print {$DumpFH} "vars = \n";
      
      for my $k (sort {$a<=>$b} (keys %fix)) {
         if ($opt->{Hash}) {
            for my $k2 (sort keys(%_exist) ) {
               printf {$DumpFH} "%20s => %s\n", "\${$k}{$k2}", "${$k}{$k2}";
            }
         } else {
            printf {$DumpFH} "%10s => %s\n", "\${$k}", "${$k}";
         }
      }
   }
}




