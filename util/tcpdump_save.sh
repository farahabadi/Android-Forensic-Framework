#!/bin/bash

save_address=$1
scenario=$2

adb pull -a /sdcard/$scenario.pcap $save_address