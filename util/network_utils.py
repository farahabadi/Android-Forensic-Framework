import subprocess
import time
import signal

def create_tcpdump(save_address, scenario_name):
    
    proc  = subprocess.Popen(["util/tcpdump.sh", save_address, scenario_name])
    try:
        while(1):
            time.sleep(10)

    except KeyboardInterrupt:
        proc.send_signal(signal.SIGINT)
        subprocess.Popen(["util/tcpdump_save.sh", save_address, scenario_name])