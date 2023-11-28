#!/usr/bin/env perl

# comment without indent
my $a = 1;
if ( $a == 1 ) {
   # comment with indent
   print "a=$a\n";
}

sub test {
   my $b = 2;

   if ( $a == 1 ) {
      print "a=$a\n";
   }

   if ( $b == 2 ) {
      # comment with indent
      # comment with indent 2
      print "b=$b\n";

   }

}

__END__
perltidy --indent-columns=3 \
         --cuddled-else \
         --maximum-line-length=120 \
         --no-outdent-long-comments \
         --noblanks-before-comments \
         --ignore-side-comment-lengths \
   < perltidy_test_comment_indent.pl
