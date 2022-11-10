package TPSUP::XLSX;

use strict;
use base qw( Exporter );
our @EXPORT_OK = qw(
   csv_to_xlsx
   xlsx_to_csvs
);

use warnings;
use Data::Dumper;
use Carp;
use TPSUP::UTIL qw(get_tmp_file get_out_fh);
use TPSUP::CSV qw(query_csv2);

sub csv_to_xlsx {
   my ($csvs, $output, $opt) = @_;
   
   # https://stackoverflow.com/questions/18899136/modifying-an-xlsx-file-excel-2007-and-newer
   # https://metacpan.org/pod/distribution/Excel-Writer-XLSX/lib/Excel/Writer/XLSX.pm
   
   require Excel::Writer::XLSX;
   
   my $out_fh = get_out_fh($output); # this creates any dir structure if needed
   close $out_fh;
   
   my $workbook = Excel::Writer::XLSX->new("$output");
   
   my $format_content = $workbook->add_format(font => 'Courier New', size => 9, align => 'left');
   $format_content->set_left(4);
   $format_content->set_right(4);
   
   my $format_header = $workbook->add_format(font => 'Courier New', size => 9, align => 'center', bold => 1);
   $format_header->set_bottom(1);
   
   my $tab_idx = 0;
   
   for (my $i=0; $i<scalar(@$csvs); $i++) {
      my $csv = $csvs->[$i];
   
      my $ref = query_csv2($csv, {%$opt, NoPrint=>1});
   
      croak "cannot parse $csv" if $ref->{status} ne 'OK';
   
      my $i_add_1 = $i+1;
   
      my $tabname = defined($opt->{TabNames}->[$i]) ? $opt->{TabNames}->[$i] : "sheet$i_add_1";
   
      my $worksheet = $workbook->add_worksheet("$tabname");
   
      my @columns = @{$ref->{columns}};
   
      my $total_col = scalar(@columns);
   
      my $j= 0; # row count
   
      for (my $col=0; $col<$total_col; $col++) {
         $worksheet->write($j, $col, $columns[$col], $format_header);
      }
   
      for my $r ( @{$ref->{array}} ) {
         $j++;

         for (my $col=0; $col<$total_col; $col++) {
            $worksheet->write($j, $col, $r->{$columns[$col]}, $format_content);
         }
      }
   }
   
   $workbook->close();
}
   
sub xlsx_to_csvs {
   my ($xlsx, $output_prefix, $opt) = @_;
   
   my $need_this_tab;
   if ($opt->{ExtractTabNames}) {
      for my $tab ( @{$opt->{ExtractTabNames}} ) {
         $need_this_tab->{$tab} ++;
      }
   }
   
   # http://www.unix.com/shell-programming-and-scripting/222095-perl-script-convert-xlsx-xls-files-csv-file.html
   #require Spreadsheet::ParseExcel;
   require Spreadsheet::XLSX;
   
   #

   croak "$xlsx not found" if ! -f $xlsx;
   
   my $excel = Spreadsheet::XLSX -> new ($xlsx);
   
   my $i = 0;
   
   for my $sheet (@{$excel -> {Worksheet}}) {
      my $output;
   
      if ($output_prefix eq '-') {
         $output = '-';
      } else {
         $output = sprintf("%s%d%s", $output_prefix, $i+1, ".csv");
      } 
      
      my $sheet = $excel->{Worksheet}[$i];
      
      $opt->{verbose} && print STDERR "------- SHEET:", $sheet->{Name}, "\n";
      
      next if $need_this_tab && defined($sheet->{Name}) && !$need_this_tab->{$sheet->{Name}};
   
      next unless defined $sheet->{MaxRow};
      next unless $sheet->{MinRow} <= $sheet->{MaxRow};
      next unless defined $sheet->{MaxCol};
      next unless $sheet->{MinCol} <= $sheet->{MaxCol};
      
      my @a;
      
      for my $row_index ($sheet->{MinRow} .. $sheet->{MaxRow}) {
         my @b;
      
         for my $col_index ($sheet->{MinCol} .. $sheet->{MaxCol}) {
            my $cell = $sheet->{Cells}[$row_index][$col_index];
      
            if ($cell) {
               #print "( $row_index , $col_index ) =>", $cell->Value, "\t";
               #print {$out_fh} $cell->Value, ",";
               push @b, $cell->Value;
            }
         }
      
         #print {$out_fh} "\n";
         push @a, \@b;
      }
      
      #close $out_fh if $out_fh && $out_fh != \*STDOUT;
      query_csv2(\@a, {%$opt, InputType=>'ArrayArray', output=>$output});

      $i++;
   }

   return;
}

1
