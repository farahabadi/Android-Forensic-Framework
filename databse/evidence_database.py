from subprocess import call
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..',)))
from extract import extraction
from addresses import get_address


def create_database():
  #make dir for database
  project_address = get_address("project_dir")

  
def extract_and_save(whole, app_name):
    project_address = get_address("project_dir")
    extraction.extract_data(project_address, whole, app_name)


###################################################################################################################

                    

# def load_database(type):
#   if (type == "all"):
#     #TODO
#   elif (type == "extension"):
#   elif (type == "app")
