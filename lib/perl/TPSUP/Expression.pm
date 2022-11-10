package TPSUP::Expression;
#use Exporter;
#our @ISA = 'Exporter';
#our @EXPOPT = qw(%fix);

# http://www.softpanorama.org/Scripting/Perlorama/perl_namespaces.shtml

# "eval '...' statements, as well as regular expressions with deferred evaluation 
# (like s///e operators or $(${ }) expressions), re-establish the namespace environment
# for the duration of the expression compilation."

#don't use 'my' for the following variables, 'my' will make them not accessible as
#$TPSUP::Expression::fix{hello} for example.
#my %fix;
#my $RESET;
#my $FIX;
#my $Prefix;
#my $verbose;
#see http://www.softpanorama.org/Scripting/Perlorama/perl_namespaces.shtml

#without 'my *fix', $TPSUP::Expression::fix{hello} is a global variable, accessible anywhere
#with 'my *fix', $TPSUP::Expression::fix{hello} will not exist in the main (calling) script
# with the 'my' above commented out, we need the following 'no strict ..' to
# disable the compiler's complain.

# for example, to set a variable from another program
#    use TPSUP::Expression;
#    no warnings 'once';   # this prevents: Name ... used only once: possible typo.
#    $TPSUP::Expression::myvar = 1;
#    @TPSUP::Expression::myarray = (1,2);
#    $TPSUP::Expression::myhash = {};
#    $TPSUP::Expression::myhash{firstname} = 'jack';

use strict;
no strict 'refs' ;
no strict 'vars';

# This is old Charlie Huckle's version. It assumes the same set of variables.
# Becasuse there is no reset before each initialization, old variable values
# could spill over into a new call.

sub export {
   while (@_) {
      my ($k, $v) = splice(@_, 0, 2);
      next unless defined $k;
      ${$k} = $v;
   }
}

# export_var is an enhanced version.
# 1. it took care of the reset need as an option
# 2. it help handle numeric variable ${35} as fix variable $fix{35}
# 3. it handles Hash-of-Hash input: set $opt->{Hash} to 1

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
               # this is nested
               for my $k2 (keys %{${$prefix}{$k}}) {
                  delete ${$prefix}{$k}{$k2};
               }
            }

            undef ${$prefix}{$k}; 
            delete ${$prefix}{$k};
         }
      } elsif ($opt->{FIX} || $FIX ) {
         %fix = ();
      } else {
         for my $k (keys %_exist) {
            if ( $opt->{Hash} ) {
               # this is nested
               for my $k2 (keys %{$k}) {
                  delete ${$k}{$k2};
               }
            }
            undef ${$k};
         }

         %_exist = ();
      }
   }

   # This is a workaround to modify $1, $2, ..., eg, ${35} = D
   # The following don't work
   # $ perl -e '${"35"} = "D"'
   # $ perl -e '${35} = "D"'
   # Modification of a read-only value attempted at -e line 1.
   #
   # The following work
   # $ perl -e '$fix{35} = "D"'
   # $ perl -e '$fix{"35"} = "D"'
   
   if ($prefix) {
      for my $k (keys %$ref) {
        if ($opt->{Hash}) {
           # this is nested
           for my $k2 (keys %{$ref->{$k}}) {
              ${$prefix}{$k}{$k2} = $ref->{$k}->{$k2};
           }
        } else {
          ${$prefix}{$k} = $ref->{$k};
        }
     }
   } elsif ($opt->{FIX}||$FIX) {
      for my $k (keys %$ref) {
         if ($opt->{Hash}) {
            for my $k2 (keys %{$ref->{$k}}) {
               $fix{$k}{$k2} = $ref->{$k}->{$k2};
            }
         } else {
            $fix{$k} = $ref->{$k};
         }
      }
   } else {
      for my $k (keys %$ref) { 
         if ($opt->{Hash}) {
            for my $k2 (keys %{$ref->{$k}}) {
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

   if ($opt->{FIX}||$FIX) {
      print {$DumpFH} "\%fix =\n";

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
      print {$DumpFH} "vars =\n";

      for my $k (sort {$a<=>$b} (keys %_exist)) {
         if ($opt->{Hash}) {
            for my $k2 (sort keys(%{$k}) ) {
               printf {$DumpFH} "%20s => %s\n", "\${$k}{$k2}", "${$k}{$k2}";
            }
         } else {
               printf {$DumpFH} "%10s => %s\n", "\$$k", "${$k}";
         }
      }
   }
}   

sub get_value {
    my ($k, $opt) = @_;

    if ($opt->{FIX}||$FIX) {
        return $fix{$k};
    } else {
       return ${$k};
    }
}

sub get_all {
   my ($k, $opt) = @_;

   if ($opt->{FIX}||$FIX) {
      return {%fix};
   } else {
      my $r;
      for my $k (keys %_exist) {
         $r->{$k} = ${$k};
      }
      return $r;
   }
}


sub get_fix_value {
    my ($k) = @_;
    return $fix{$k} ;
}

sub convert_to_fix_expression {
   my ($exp, $opt) = @_;

   # This is a workaround to modify $1, $2, ..., eg, ${35} = D
   # The following don't work
   # $ perl -e '${"35"} = "D"'
   # $ perl -e '${35} = "D"'
   # Modification of a read-only value attempted at -e line 1.
   #
   # The following work
   # $ perl -e '$fix{35} = "D"'
   # $ perl -e '$fix{"35"} = "D"'
   
   my $workaround_exp = $exp;
   $workaround_exp =~ s:\$\{:\$fix{:g;
   
   return $workaround_exp;
}
   
my $ compiled_by_exp;
   
sub compile_exp {
   my ($exp, $opt) = @_;
   #print STDERR "compile_exp opt =", Data::Dumper::Dumper($opt);
   
   if (exists $compiled_by_exp->{$exp}) {
      return $compiled_by_exp->{$exp};
   }

   print STDERR "compile exp='$exp'\n" if $opt->{verbose} || $verbose;

   my $workaround_exp;

   if ($opt->{FIX} || $FIX) {
      # This is a workaround to modify $1, $2, ..., eg, ${35} = D
      # The following don't work
      # $ perl -e '${"35"} = "D"'
      # $ perl -e '${35} = "D"'
      # Modification of a read-only value attempted at -e line 1.
      #
      # The following work
      # $ perl -e '$fix{35} = "D"'
      # $ perl -e '$fix{"35"} = "D"'
   
      $workaround_exp = convert_to_fix_expression($exp);
   
      ($opt->{verbose} || $verbose) && print STDERR "converted '$exp' to '$workaround_exp'\n";
   } else {
      $workaround_exp = $exp;
   }
   
   my $warn = ($opt->{verbose}||$verbose) ? 'use' : 'no';
   
   my $compiled = eval "$warn warnings; no strict; package TPSUP::Expression; sub { $workaround_exp } ";

   if ($@) {
      if ($opt->{FIX} || $FIX) {
         die "Bad match expression '$workaround_exp', converted from '$exp': $@";
      } else {
         die "Bad match expression '$workaround_exp': $@";
      }
   }
   
   $compiled_by_exp->{$exp} = $compiled;
   
   return $compiled;
   
}
   
sub strcat {
   return join ("", @_);
}
   
sub indexof {
   my ($string, $substring) = @_;
   return index($string, $substring);
}
   
sub lindexof {
   my ($string, $substring) = @_;
   return rindex($string, $substring);
}

sub regexp {
   my ($string, $pattern) = @_;

   return $string =~ /$pattern/;
}

sub regsub {
   my ($string, $sub) = @_;
   eval "\$string =~ $sub";
   return $string;
}

sub cond {
   my ($bool, $ValueIfTrue, $ValueIfFalse) = @_;
   return $bool ? $ValueIfTrue : $ValueIfFalse;
}

sub get_desc_by_tag_value {
   return TPSUP::FIX::get_desc_by_tag_value(@_);
}

sub fixdesc {
   my ($tag, $opt) = @_;
   #return TPSUP::FIX::get_desc_by_tag_value($tag, get_fix_value($tag));
   return TPSUP::FIX::get_desc_by_tag_value($tag, $TPSUP::Expression::fix{$tag});
}

###########################################################################
#
# Each calling script (module) can also add new functions
# into this name space TPSUP::Expression
#
# For example, add a fixdesc2() function.
#
# . . .
# exit 0; # end of the script
#
# package TPSUP::Expression;
# # If you want to use $fix{$tag} instead of long-typing $TPSUP::Expression::fix{$tag}
# # (see below), you need to declare %fix here
# # my %fix;
#
# sub fixdesc2 {
# my ($tag, $opt) = @_;
#
# # the following 2 are the same.
# #return TPSUP::FIX::get_desc_by_tag_value($tag, get_fix_value($tag));
# return TPSUP::FIX::get_desc_by_tag_value($tag, $TPSUP::Expression::fix{$tag});
# } 
#
# 1
#
# Note: you have to announce the name space with "package TPSUP::Expression"
# and end the name space with "1".
###########################################################################

1
