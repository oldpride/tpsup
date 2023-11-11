package TPSUP::FILE;

use strict;
use warnings;

use base qw( Exporter );
our @EXPORT_OK = qw(
  tpglob
  get_mtime
  tpfind
);

use Carp;
use Data::Dumper;

use TPSUP::UTIL qw(
  get_user_by_uid
  get_group_by_gid
  compile_perl_array
  transpose_arrays
);

sub tpglob {
    my ( $pattern, $flags ) = @_;

    my @patterns;
    my $type = ref($pattern);
    if ( !$type ) {

        # scalar
        @patterns = split /\s+/, $pattern;
    }
    elsif ( $type eq 'ARRAY' ) {

        # array
        @patterns = @$pattern;
    }
    else {
        croak "tpglob: pattern must be scalar or array";
    }

    my @files;
    for my $p (@patterns) {
        my @files2 = glob($p);
        if (@files2) {
            push @files, @files2;
        }
        else {
            print STDERR "tpglob: no file matches pattern '$p'\n";
        }
    }

    # print "tpglob: files=", Dumper( \@files );
    return @files;
}

sub sorted_files {
    my ( $files, $opt ) = @_;

    my $globbed   = $opt->{globbed};
    my $reverse   = $opt->{reverse};
    my $sort_func = $opt->{sort_func};

    my @files2;
    if ( !$globbed ) {
        @files2 = tpglob( $files, $opt );
    }
    else {
        @files2 = @$files;
    }

    if ( !$sort_func ) {
        $sort_func = sub { $_[0] cmp $_[1] };
    }

    my @sorted_files = sort { $sort_func->( $a, $b ) } @files2;
    return $reverse ? reverse @sorted_files : @sorted_files;
}

my $mtime_by_file;

sub get_mtime {
    my $file = shift;

    if ( !$mtime_by_file->{$file} ) {

        # my @array = lstat($file);
        # my (
        #     $dev,  $ino,   $mode,  $nlink, $uid,     $gid, $rdev,
        #     $size, $atime, $mtime, $ctime, $blksize, $blocks
        # ) = @array;
        $mtime_by_file->{$file} = ( stat($file) )[9];
    }

    return $mtime_by_file->{$file};
}

sub convert_filemode {
    my ( $input, $action ) = @_;

    my $mode;
    if ( $action eq 'int2oct' ) {
        $mode = sprintf( "%04o", $input );
    }
    elsif ( $action eq 'oct2int' ) {
        $mode = oct($input);
    }
    elsif ( $action eq 'int2str' ) {
        $mode = sprintf( "%04b", $input );

        # use left shift to convert octal to string
    }
    else {
        croak "unknown action=$action";
    }

}

sub sorted_files_by_mtime {
    my ( $files, $opt ) = @_;

    my $sort_func = sub {
        my ( $f1, $f2 ) = @_;
        my $mtime1 = get_mtime($f1);
        my $mtime2 = get_mtime($f2);
        return $mtime1 <=> $mtime2;
    };

    my $opt2 = $opt ? $opt : {};
    return sorted_files( $files, { %$opt2, sort_func => $sort_func } );
}

sub get_latest_files {
    my ( $files, $opt ) = @_;

    my $opt2 = $opt ? $opt : {};
    my @sorted_files =
      sorted_files_by_mtime( $files, { %$opt2, reverse => 1 } );
    return \@sorted_files;
}

sub tpfind {
    my ( $paths, $opt ) = @_;

    my $verbose   = $opt->{verbose} || 0;
    my $find_dump = $opt->{find_dump};
    my $find_ls   = $opt->{find_ls};
    my $MaxDepth  = $opt->{MaxDepth};
    my $Enrich    = $opt->{Enrich} || $find_ls;

    # compile Exps into package TPSUP::Expression (namespace)
    my $MatchExps;
    if ( $opt->{MatchExps} && @{ $opt->{MatchExps} } ) {
        $MatchExps = compile_perl_array( $opt->{MatchExps} );
    }

    print STDERR "MatchExps=", Dumper($MatchExps) if $verbose;

    my $Handlers;
    if (   $opt->{HandleExps}
        && @{ $opt->{HandleExps} }
        && $opt->{HandleActs}
        && @{ $opt->{HandleActs} } )
    {

        my $exps = compile_perl_array( $opt->{HandleExps} );
        my $acts = compile_perl_array( $opt->{HandleActs} );

        $Handlers = transpose_arrays(
            [ $exps, $acts, $opt->{HandleExps}, $opt->{HandleActs} ], $opt );
    }

    my $FlowControl;
    if (   $opt->{FlowExps}
        && @{ $opt->{FlowExps} }
        && $opt->{FlowDirs}
        && @{ $opt->{FlowDirs} } )
    {

        my $exps = compile_perl_array( $opt->{FlowExps} );
        my $dirs = $opt->{FlowDirs};

        $FlowControl = transpose_arrays(
            [ $exps, $dirs, $opt->{FlowExps}, $opt->{FlowDirs} ], $opt );
    }

    my $ret = { error => 0, count => 0, hashes => [] };

    # start - function inside function
    my $process_node = sub {
        my $path = shift;

        my $result = {};

        if ( $verbose > 1 ) {
            print "process_node() is checking $path\n";
        }

        my $type =
            ( -f $path ) ? 'file'
          : ( -d $path ) ? 'dir'
          : ( -l $path ) ? 'link'
          :                'unknown';

        my (
            $dev,  $ino,   $mode,  $nlink, $uid,     $gid, $rdev,
            $size, $atime, $mtime, $ctime, $blksize, $blocks
        ) = lstat($path);

        my $user = get_user_by_uid($uid);
        $user = $uid if !$user;

        my $group = get_group_by_gid($gid);
        $group = $gid if !$group;

        my $now = time();

        my $short = $path;
        $short =~ s:.*/::;

        my $r;

   # mystery: for some reason, 'user' cannot be used in the expresssion. changed
   # to use 'owner' instead
   # @{$r}{qw(path type mode uid gid size mtime user group now)}
   #  = ($path, $type, $mode, $uid, $gid, $size, $mtime, $user, $group, $now);

        @{$r}{
            qw(path    type   mode   uid   gid   size   mtime   owner  group   now   short)
          } = (
            $path,  $type, $mode,  $uid, $gid, $size,
            $mtime, $user, $group, $now, $short
          );

        $r->{mode_oct} = sprintf(
            "%04o", $mode    #& 07777
        );

        if ($Enrich) {
            my ( $sec, $min, $hour, $mday, $mon, $year, $wday, $yday, $isdst )
              = localtime($mtime);
            $r->{mt_string} = sprintf(
                "%04d%02d%02d-%02d:%02d:%02d",
                $year + 1900,
                $mon + 1, $mday, $hour, $min, $sec
            );
            $r->{mt_yyyymmdd} =
              sprintf( "%04d%02d%02d", $year + 1900, $mon + 1, $mday );
        }

        print "r=", Dumper($r) if $verbose > 1;

        if ( $Handlers || $FlowControl ) {

            TPSUP::Expression::export_var( $r, { RESET => 1 } );

#TPSUP::Expression::dump_var(); # I can see 'user' was populated even at this step

            if ($verbose) {
                $TPSUP::Expression::verbose = 1;
            }
        }

        if ($FlowControl) {
            for my $row (@$FlowControl) {
                my ( $match, $direction, $match_code, $direction_code ) = @$row;

                if ( $match->() ) {
                    if ($verbose) {
                        print STDERR "matched:   $match_code\n",
                          "direction: $direction_code\n";
                    }

                    if ( $direction eq 'prune' ) {
                        $result->{direction} = 'prune';
                        next;
                    }
                    elsif ( $direction eq 'exit' ) {
                        $result->{direction} = 'exit';
                        return $result;
                    }
                    else {
                        croak "unknown FlowControl driection='$direction'";
                    }
                }
            }
        }

        if ($Handlers) {
          ROW:
            for my $row (@$Handlers) {
                my ( $match, $action, $match_code, $action_code ) = @$row;

                if ( $match->() ) {
                    if ($verbose) {
                        print STDERR "matched: $match_code\n",
                          "action:  $action_code\n";
                    }
                }
                else {
                    next ROW;
                }

                if ( !$action->() ) {
                    print STDERR "ERROR: action failed at path=$path\n";
                    $result->{error}++;
                }
            }
        }

        if ($MatchExps) {

            # MatchExps doesn't affect flow control;
            # it only affects whether to count or print the path
            # therefore, we put this after FlowControl
            my $match_all = 1;
            for my $i ( 0 .. $#$MatchExps ) {
                my $match = $MatchExps->[$i];
                my $code  = $opt->{MatchExps}->[$i];

                print STDERR "code=$code, path=$path\n";

                if ( $match->() ) {
                    if ($verbose) {
                        print STDERR "matched: $code\n";
                    }
                }
                else {
                    $match_all = 0;
                    last;
                }
            }
            if ( !$match_all ) {
                return $result;
            }
        }

        push @{ $ret->{hashes} }, $r;
        $ret->{count}++;

        if ($find_dump) {
            print Dumper($r);
        }
        elsif ($find_ls) {
            print
"$r->{mode_oct} $r->{owner} $r->{group} $r->{size} $r->{mt_string} $r->{path}\n";
        }
        else {
            print "$r->{path}\n";
        }

        return $result;
    };

    # end - function inside function

    my @pathLevels;
    for my $path (@$paths) {
        my $pathLevel = [ $path, 0 ];
        push @pathLevels, $pathLevel;
    }

    my $level = 0;
    my %seen;

    while ( my $pathLevel = shift @pathLevels ) {
        my ( $path, $level ) = @$pathLevel;
        my $result = $process_node->($path);
        if ( exists $result->{direction} ) {
            if ( $result->{direction} eq 'prune' ) {
                next;
            }
            elsif ( $result->{direction} eq 'exit' ) {
                return $ret;
            }
        }

        next if defined($MaxDepth) && $level >= $MaxDepth;

        if ( -d $path ) {
            opendir( DIR, $path ) or die "Cannot open $path\n";
            my @shorts = readdir(DIR);
            closedir(DIR);
            for my $short (@shorts) {
                next
                  if $short eq '.'
                  || $short eq '..'
                  || $short eq '.git'
                  || $short eq '.snapshot'
                  || $short eq '.idea'
                  || $short eq '.vscode'
                  || $short eq '__pycache__';

                my $path2 = "$path/$short";
                next if $seen{$path2};
                $seen{$path2} = 1;

                my $pathLevel = [ $path2, $level + 1 ];
                push @pathLevels, $pathLevel;

            }
        }
    }

    return $ret;
}

sub main {
    use TPSUP::TEST qw(test_lines);

    # use 'our' in test code, not 'my'
    my $test_code = <<'END';
        our $TPSUP = $ENV{TPSUP};
        our $files = "$TPSUP/python3/lib/tpsup/searchtools_test*";
        TPSUP::FILE::tpglob([$files]);
        TPSUP::FILE::sorted_files_by_mtime($files);
        TPSUP::FILE::sorted_files_by_mtime($files, {reverse=>1});
        ${TPSUP::FILE::get_latest_files($files)}[0];     # convert result to array
        @{TPSUP::FILE::get_latest_files($files) }[0..1]; # slice
END

    test_lines($test_code);
}

main() unless caller();

1
