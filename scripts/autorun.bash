#!/bin/bash

usage () {
   cat <<EOF
usage:

   $0 joblist.txt

Run job one-by-one from joblist.txt

One job a line.

Commented lines (starting with #) or blank lines will be skipped.

   -d        debug  mode
   -n        dryrun mode, to check whether jobs are in: OH, OI

EOF

   exit 1
}

dryrun=N

while getopts dn o;
do
   case "$o" in
      d) set -x;;
      n) dryrun=Y;;
      *) echo "unknow switch"; usage;;
   esac
done

shift $((OPTIND-1))

if [ $# -ne 1 ]; then
   echo "wrong number of args"
   usage
fi

jobfile=$1

if [ ! -f $jobfile ]; then
   echo "joblist file '$jobfile' not found"
   exit 1
fi

jobnames=`cat $jobfile|egrep -v '^\s*#|^\s*$'`
jobcount=`echo "$jobnames"|wc -l`

# verify that autosys settings are in place
if [ "X$AUTOSERV" = "X" ]; then
   echo  
   echo "Did not find an Autosys Server defined. Please source Autosys settings file."
   echo 
   exit 1
fi

jobindex=0
final_report=""

for j in `echo $jobnames`;
do
   jobindex=$(($jobindex + 1))
   # Get all job names referenced by given name - may be wildcard or box
   echo -n "Collecting jobs matching '$j' ($jobindex of $jobcount) on $AUTOSERV -"
   autorep_before=`autorep -J $j`

   # list of job names in this query
   # remove heading space chars
   # condense multiple space chars into one
   sublist=`echo "$autorep_before" | egrep -v '^$|^Job Name|^_____' | \
            sed 's/^\s\s*//; s/\s\s\s*/ /g' | cut -d' ' -f1`
   
   # Capture just one set of headers for the final report
   if [ "$final_report" = "" ]; then
      final_report=`echo "$autorep_before" | head -3`
   fi

   # If any are currently held or on ice, report it and exit
   subcount=0
   suberror=0
   for i in `echo $sublist`;
   do
      subcount=$(($subcount + 1))

      # extra space in "^$i " to prevent job 'ABC' from matching 'ABCD'
      # caret char  in "^$i " to prevent job 'ABC' from matching 'EABC'
      if echo "$autorep_before" | grep "^$i " | egrep " OH | OI " >/dev/null; then
         suberror=$(($suberror + 1))
      fi
   done

   if [ $suberror -ne 0 ]; then
      echo "$subcount jobs found"
      echo
      echo "$autorep_before"
      echo
      echo "ABORTING - $suberror jobs not runnable."
      echo
      exit 1
   else
      echo " running $subcount jobs ..."
   fi

   # Run current job(s) in sequence.
   if [ $dryrun = N ]; then
      (set -x; sendevent -E FORCE_STARTJOB -J $j)
   else
      echo "dryrun: sendevent -E FORCE_STARTJOB -J $j"
      continue;
   fi

   interval=10
   # Monitor all jobs in this sublist for completion
   while :
   do
      autorep_after=`autorep -J $j`

      runcount=0
      suberror=0

      # check each job in $sublist for SU, TE, or FA. 
      # Add 1 to $runcount when found. Add 1 to $suberror if not SU.
      for i in `echo $sublist`
      do
         line_before=`echo "$autorep_before" | egrep "^[ ]*$i "`
         line_after=` echo "$autorep_after"  | egrep "^[ ]*$i "`

         if [ "$line_before" != "$line_after" ]; then
            if [[ $line_after =~ ( SU | TE | FA ) ]]; then
               runcount=$(($runcount + 1))
            fi

            if [[ $line_after =~ ( TE | FA ) ]]; then
               suberror=$(($suberror + 1))
            fi
         fi
      done

      # If jobs remain incomplete, sleep 10 secs and try again
      if [ $runcount -lt $subcount ] && [ $suberror -eq 0 ]; then
         echo "Only $runcount of $subcount compelete. Sleep for $interval."
         sleep $interval
         if [ $interval -lt 60 ]; then
            interval=`expr $interval + 10`
         fi
      else
         # capture final state to overall final report
         final_report="$final_report`echo; echo \"$autorep_after\" | tail -$runcount`"
         break
      fi
   done

   echo "$final_report"
   echo

   # if any failures seen, report and quit
   if [ $suberror -ne 0 ]; then
      echo "ABORTING - $suberror jobs did not complete successfully."
      echo
      exit 0
   fi
done
