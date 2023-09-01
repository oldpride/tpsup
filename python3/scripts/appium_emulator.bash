#!/usr/bin/bash

prog=$(basename $0)

usage () {
    cat >&2 <<END
usage:

    $prog start|stop|check

    start|stop|check: Appium Server + adb + emulator

END
    exit 1
}

if [ $# -ne 1 ]; then
    usage
fi

action=$1

if [ "$action" = "start" ]; then
    echo "starting Appium Server + adb + emulator"
    appium_steps -is_emulator key=home
elif [ "$action" = "stop" ]; then
    echo "stopping Appium Server + adb + emulator"
    python -c "import tpsup.appiumtools; tpsup.appiumtools.check_proc(kill=True)"
elif [ "$action" = "check" ]; then
    echo "checking Appium Server + adb + emulator"
    python -c "import tpsup.appiumtools; tpsup.appiumtools.check_proc()"
else
    usage
fi