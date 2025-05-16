#!/bin/bash

save_address=$1
scenario=$2


cleanup() {
    adb pull -a /sdcard/$scenario.pcap $save_address/$scenario.pcap
    exit 0
}

trap cleanup SIGINT

adb_state=$(adb get-state 2>/dev/null)
if [ ! $adb_state ]
then
    echo no devices connected!
    exit 1
fi

b=$(adb shell command -v su)

if [ -z $b ]
then
    echo su not foundd!
    exit 0
else
    adb shell su -c tcpdump -i any -w /sdcard/$scenario.pcap
fi

