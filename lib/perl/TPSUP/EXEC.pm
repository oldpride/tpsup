package TPSUP::EXEC;

sub exec_into_global {
   my ( $code, $opt ) = @_;

   my $verbose = $opt->{verbose} ? $opt->{verbose} : 0;

   my $dict = $opt->{dict} ? $opt->{dict} : {};

   if ($verbose) {
      print "------ begin preparing code ------\n";
      print "original code: $code\n";
   }

   $code = resolve_scalar_var_in_string( $code, $dict, $opt );

   if ($verbose) {
      print "afer substituted scalar vars in '{{...}}': $code\n";
      eval "no warnings;
            print qq(after eval'ed code: $code\n);
            use warnings;
           ";
   }

   # use a sub{} to separate compile-time error and run-time error
   #    compile-time error should be handled right here
   #        run-time error should be handled by caller

   my $func;
   eval "\$func = sub { $code }";
   if ($@) {
      # compile-time error happens here
      my $numbered_code = add_line_number_to_code($code);
      croak "failed to compile code='
$numbered_code
$@
      '\n";
   }
   $func->();    # run-time error happens here
}
