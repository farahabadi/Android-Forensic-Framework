#!/bin/bash

if [ -z $1 ] || [ -z $2 ]
then
    echo no input
    exit 1
fi

address=$1
root=$2


echo $address
echo $root


adb_state=$(adb get-state 2>/dev/null)
if [ ! $adb_state ]
then
    echo no devices connected!
    exit 1
fi

b=$(adb shell command -v su)
echo b: $b

if [ -z $b ]
then
    echo su not found
    echo dumping in non root mode
    mkdir -p $address
    adb pull /sdcard $address
else
    if [ $root == "root" ]
    then
        echo su found
        echo dumping in root mode
	mkdir -p $address
	adb shell mkdir /sdcard/data-1
	adb shell su -c 'cp -r /data /sdcard/data-1'
	adb pull /sdcard/data-1 $address/private
	adb pull /sdcard $address/public
    fi	
fi
#a=$(adb shell su -c ls 2>/dev/null)
#echo $a
