import subprocess
import os

# Please Add your pckage name in list below seperated by ','
app_modules = ["org.telegram.messenger"]


global_project_name = ""

def create_dirs():
    for item in ["project_dir", "project_extract", "project_extract_media", "project_extract_media", "project_extract_app", "project_extract_other",
                  "project_extract_network", "project_process", "project_process_face", "project_process_extension", "project_process_extension_image",
                    "project_process_network", "project_process_apps"]:
        address = get_address(item)
        os.makedirs(address, exist_ok=True)
        # subprocess.call(["mkdir -p", address])

def get_address(needed_address):
    base_address = ("projects/" + global_project_name).strip()
    match needed_address:
        #base address
        case "project_dir":
            return base_address
        
        # extract
        case "project_extract":
            return base_address + "/extract"
        case "project_extract_media":
            return base_address + "/extract/media/sdcard"
        case "project_extract_app":
            return base_address + "/extract/apps_data"
        case "project_extract_other":
            return base_address + "/extract/other"
        case "project_extract_network":
            return base_address + "/extract/network"

        
        # processed address
        case "project_process":
            return base_address + "/processed_data"
        case "project_process_face":
            return base_address + "/processed_data/faces"
        case "project_process_extension":
            return base_address + "/processed_data/extension"
        case "project_process_extension_image":
            return base_address + "/processed_data/extension/image"
        case "project_process_network":
            return base_address + "/processed_data/network"
        case "project_process_apps":
            return base_address + "/processed_data/apps"

def get_current_project_name():
    return global_project_name

def set_current_project_name(name):
    global global_project_name
    global_project_name = name

def is_app_modules(name):
    global app_modules
    if (name in app_modules):
        return True
    else:
        return False

def get_app_modules():
    global app_modules
    return app_modules