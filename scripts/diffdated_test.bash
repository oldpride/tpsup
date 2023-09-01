#!/bin/bash

basedir=~/diffdir

[ -e $basedir ] && /bin/rm -fr $basedir

today=`date +%Y%m%d`

mode=644
size=59

make_dated_dir () {
   yyyymmdd=$1
   yyyy=`echo $yyyymmdd|cut -c1-4`
     mm=`echo $yyyymmdd|cut -c5-6`
     dd=`echo $yyyymmdd|cut -c7-8`

   mkdir -p $basedir/p1/$yyyymmdd

   if [ $yyyymmdd = $today ]; then
      # bash $RANDOM gives a random number every time.
      make_file $mode $size "$yyyymmdd 03:00:00" $basedir/p1/p1_stdout_$RANDOM.log
      make_file $mode $size "$yyyymmdd 03:00:00" $basedir/p1/p1_stderr_$RANDOM.log
      make_file $mode $size "$yyyymmdd 06:00:00" $basedir/p1/p1_data.log
      make_file $mode $size "$yyyymmdd 06:00:01" $basedir/p1/p1_data.log.1
   else 
      make_file $mode $size "$yyyymmdd 03:00:00" $basedir/p1/$yyyymmdd/p1-stdout_${RANDOM}_$yyyymmdd.log.gz
      make_file $mode $size "$yyyymmdd 03:00:00" $basedir/p1/$yyyymmdd/p1-stdout_${RANDOM}_$yyyymmdd.log.gz
      make_file $mode $size "$yyyymmdd 03:00:00" $basedir/p1/$yyyymmdd/p1_stderr-${RANDOM}_$yyyymmdd.log.gz
      make_file $mode $size "$yyyymmdd 03:00:00" $basedir/p1/$yyyymmdd/p1_data.log.gz
      make_file $mode $size "$yyyymmdd 03:00:01" $basedir/p1/$yyyymmdd/p1_data.log.1.gz
      make_file $mode $size "$yyyymmdd 03:00:02" $basedir/p1/$yyyymmdd/p1_data.log.2.gz
      make_file $mode $size "$yyyymmdd 03:00:03" $basedir/p1/$yyyymmdd/p1_data.log.3.gz
   fi

   mkdir -p $basedir/p2/$yyyy-$mm-$dd
   make_file $mode $size "$yyyymmdd 03:00:00"    "$basedir/p2/$yyyy-$mm-$dd/p2.log"

   mkdir -p $basedir/p3/$yyyy/$mm/$dd
   if [ $yyyymmdd = $today ]; then
      make_file 600 $size "$yyyymmdd 03:00:00"    $basedir/p3/$yyyy/$mm/$dd/p3-proc2.log
   else
      make_file $mode $size "$yyyymmdd 03:00:00"    $basedir/p3/$yyyy/$mm/$dd/p3.log
      make_file $mode $size "$yyyymmdd 03:00:00"    $basedir/p3/$yyyy/$mm/$dd/p3-proc2.log
   fi

   mkdir -p $basedir/p4/$yyyy-$mm/
   if [ $yyyymmdd = $today ]; then
      make_file $mode 13 "$yyyymmdd 05:00:00"    $basedir/p4/$yyyy-$mm/stdout-p4-$mm-${dd}_$RANDOM.log.gz
      make_file $mode $size "$yyyymmdd 03:00:00"    $basedir/p4/$yyyy-$mm/stderr-p4-$mm-${dd}_$RANDOM.log.gz
   else 
      make_file $mode $size "$yyyymmdd 03:00:00"    $basedir/p4/$yyyy-$mm/stdout-p4-$mm-${dd}_$RANDOM.log.gz
   fi
}

make_file () {
   mode=$1
   size=$2
   time=$3
   path=$4

   fallocate -l $size $path  #mkfile minimal size is 1k
   chmod $mode $path
   touch -d "$time" $path
}

for n in 1 2 3 4 5 6 
do
   make_dated_dir `tradeday -$n`
done
make_dated_dir $today

#find $basedir -type f -ls
# use 'ls' command get sorted and shortened output
ls -l `find $basedir -type f`
