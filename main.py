from databse import evidence_database
from analyze import process
from addresses import get_address, set_current_project_name, create_dirs



def start_project(name, whole, app_name):  
  set_current_project_name(name)
  create_dirs()

  evidence_database.create_database()
  process_address = get_address("project_process")
  extracted_address = get_address("project_extract")

  print("start extraction")

  # extract data
  evidence_database.extract_and_save(whole, app_name)

  print("start processing")
  # process data
  process.start_process(extracted_address, process_address, whole, app_name)
