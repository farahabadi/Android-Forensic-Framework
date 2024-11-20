#!/bin/bash

if [ -z $1 ]
then
    echo no input
    exit 1
fi

address=$1


echo extract address is: $address
echo starting to dump...
sleep 2


adb_state=$(adb get-state 2>/dev/null)
if [ ! $adb_state ]
then
    echo no devices connected!
    exit 1
fi

b=$(adb shell command -v su)
echo b: $b

adb shell mkdir /sdcard/data_tmp

if [ -z $b ]
then
    echo su not found
    echo dumping in non root mode
    sleep 3
    mkdir -p $address/non-root
    adb pull /sdcard $address/non-root
    list=$(adb shell ls /)
    for i in $list
    do
        if [ $i == "sys" ] || [ $i == "config" ] || [ $i == "proc" ]; then
            continue
        fi
        adb shell cp -ra $i /sdcard/data_tmp 2>/dev/null
        adb pull /sdcard/data_tmp/$i $address/non-root
        adb shell rm -rf /sdcard/data_tmp/$i
    done
else
    echo su found
    echo dumping in root mode
    sleep 3
    mkdir -p $address/root
	list=$(adb shell su -c ls /)
    for i in $list
    do
        if [ $i == "sys" ] || [ $i == "config" ] || [ $i == "proc" ] || [ $i == "dev" ]; then
            continue
        fi
        echo coping $i...
        if [ $i == "data" ]; then
            list=$(adb shell su -c ls /data)
            for j in $list
            do
                if [ $j == "media" ]; then
                    continue
                fi
            adb shell mkdir -p /sdcard/data_tmp/data
            adb shell su -c cp -ra /data/$j /sdcard/data_tmp/data 2>/dev/null
            adb pull -a /sdcard/data_tmp/data $address/root
            adb shell rm -rf /sdcard/data_tmp/data
            done
            continue
        fi
        adb shell su -c cp -ra $i /sdcard/data_tmp 2>/dev/null
        adb pull -a /sdcard/data_tmp/$i $address/root
        adb shell rm -rf /sdcard/data_tmp/$i
    done	
fi
adb shell rmdir /sdcard/data_tmp

        