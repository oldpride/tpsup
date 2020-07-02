#!/bin/bash

#
### BEGIN INIT INFO
# Provides:          mountsd_init.d
# Required-Start:    $remote_fs $syslog
# Required-Stop:     $remote_fs $syslog
# Should-Start:      $network $time
# Should-Stop:       $network $time
# Default-Start:     2 3 4 5
# Default-Stop:      0 1 6
# Short-Description: mount/umount sdcard
# Description:       mount/umount sdcard
#                    
### END INIT INFO
#

usage () {
   cat >&2 <<EOF
usage:

   $0 start
   $0 stop
   $0 status

EOF
   exit 1
}

if [ $# -ne 1 ]; then
   echo >&2 "wrong number of args"
   usage
fi

action=$1

if [ $action = start ]; then 
   mount /dev/mmcblk1p1 /media/sdcard
   df -k /media/sdcard
elif [ $action = stop ]; then 
   umount /media/sdcard
   df -k /media/sdcard
elif [ $action = status ]; then 
   df -k /media/sdcard
else 
   echo "unknown action='action'"
   usage
fi


