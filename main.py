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

# backends = [
#   # 'fast mtcnn',
#   'yolov8',
# ]

# models = [
#   # "VGG-Face",
#   "Facenet",
#   "Facenet512", 
#   # "OpenFace", 
#   # "DeepFace", 
#   # "DeepID", 
#   # "ArcFace", 
#   # "SFace",
#   # "GhostFaceNet",
# ]

# img = image_utils.open_image("/home/alireza/university/master/final-project/code/datasets/1/test2.jpg")

# for i in range(len(models)):
#     for j in range(len(backends)):
#       print("model: ", models[i], "    backend: ", backends[j])
#       similars = utils.find_faces(face=img, db="/home/alireza/university/master/final-project/code/datasets/1/res", model=models[i], backend=backends[j])
#       for k in similars:
#          for l in k['identity']:
#             print(l)



def start_project(name, whole, app_name):
  set_current_project_name(name)
  create_dirs()

  evidence_database.create_database()
  process_address = get_address("project_process")
  extracted_address = get_address("project_extract")
  
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
