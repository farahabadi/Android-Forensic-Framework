from util import image_utils
from util import network_utils
from databse import evidence_database
from extract import extraction
from analyze import process
from addresses import get_address, set_current_project_name, create_dirs
import cv2
import operator
import numpy as np
import time
import os
import keyboard
import time




def start_project(name, whole, app_name):
  set_current_project_name(name)
  create_dirs()

  evidence_database.create_database()
  process_address = get_address("project_process")
  extracted_address = get_address("project_extract")

  scenarios_time = input("how many seconds needed to do scenarios?")
  print("start scenarios. put pcap in project/extract/network")
  time.sleep(int(scenarios_time))
  # print("end scenarios in 50 seconds")
  # time.sleep(50)
  print("start extraction")

  # extract data
  # evidence_database.extract_and_save(whole, app_name)

  # process data
  process.start_process(extracted_address, process_address, whole, app_name)








####################################################################################



def start_scenarios(extracted_address, whole):
  scenario_names = input("Enter scenario names with space:")
  scenario_names = scenario_names.split(' ')
  network_save_address = get_address("project_extract_network")
  with open("{ext}/scenarios.txt".format(ext=extracted_address), 'w+') as scean_file:
    for name in scenario_names:
        print("do scenario: ", name)
        scean_file.write("{name1}\n".format(name1=name))
        if (whole):
          network_utils.create_tcpdump(network_save_address, name)
        else:
          while True:  # making a loop
            try:  # used try so that if user pressed other than the given key error will not be shown
              time.sleep(5)
            except KeyboardInterrupt:
              break




def load_case():
  #TODO
  print("s")
