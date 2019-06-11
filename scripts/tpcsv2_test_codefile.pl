sub mysum {
   my ($col, $ah) = @_;
   my $sum = 0;
   for my $r (@$ah) {
      $sum += $r->{$col};
   }
   return $sum;
}

