#!/bin/bash

address=$1
whole=$2
app_name=$3


echo starting to dump...


adb_state=$(adb get-state 2>/dev/null)
if [ ! $adb_state ]
then
    echo no devices connected!
    exit 1
fi

b=$(adb shell command -v su)
echo b: $b

adb shell rmdir /sdcard/data_tmp
adb shell mkdir /sdcard/data_tmp

if [ -z $b ]
then
    echo su not found, dumping in non root mode
    mkdir -p $address/extract/media
    adb pull -a /sdcard $address/extract/media
    list=$(adb shell pm list packages)
    for package in $list; do
        if [ $app_name != "" ]
        then
        if [ $app_name == $package ]
        then
            echo app found!
        fi
        fi
    done

else
    echo su found
    echo dumping in root mode
    mkdir -p $address/extract/apps_data $address/extract/media $address/extract/other
    ok=false
    list=$(adb shell pm list packages | cut -d  ':' -f 2)
    for package in $list; do
        if [ $app_name == $package ]
        then
            echo app found!
            ok=true
        fi
    done

    if [ $ok == "false" ]
    then
      echo app not found !!
      exit 1
    fi

    adb shell su -c cp -pr /data/data/$app_name /sdcard/data_tmp
    adb pull -a /sdcard/data_tmp/$app_name $address/extract/apps_data
    adb shell su -c rm -rf  /sdcard/data_tmp/$app_name

    adb shell mkdir /sdcard/data_tmp/important_databases
    adb shell su -c cp -rp /data/data/com.android.providers.contacts/databases/* /sdcard/data_tmp/important_databases
    adb shell su -c cp -rp  /data/data/com.android.providers.telephony/databases/* /sdcard/data_tmp/important_databases
    adb shell su -c cp -rp  /data/data/com.android.providers.calendar/databases/* /sdcard/data_tmp/important_databases
    adb pull -a /sdcard/data_tmp/important_databases $address/extract/other
    adb shell su -c rm -rf  /sdcard/data_tmp

    if [ -d $address/extract/media/sdcard ]
    then
        adb pull -a /sdcard $address/extract/media
    fi
fi

        
