import os, sys
from subprocess import call
import shutil
import cv2
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..',)))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'util')))
from addresses import get_address
from util import image_utils
from .app_process import process_app_data
from .network_process import start
from .timeline_process import process_timeline

ext_list=["archive", "app", "audio", "book", "code", "exec", "font", "image", "sheet", "slide", "text", "video", "web", "db", "others"]
ext=dict()
known_apps=[]


def start_process(address, out, whole, app_name):
    
    project_address = get_address("project_dir")

    # organise by extension
    # create_extensions()
    # extension_org(address, out)

    #face analysis
    img_address = get_address("project_process_extension_image")
    save_address = get_address("project_process_face")
    process_images(img_address, save_address)

    # apps data analysis
    app_address = get_address("project_extract_app")
    for app in app_name:
        app_address = app_address + "/" + app
        if (whole):
            process_app_data1(app, app_address)


    pcap_address = get_address("project_extract_network")
    network_output_dir = get_address("project_process_network")
    if (whole):
        print("analyze network data")
        process_network_data(pcap_address, network_output_dir)

    process_timeline(project_address)
    




def process_images(img_address, save_address):
    face_analyze(img_address, save_address)

def process_app_data1(app_name, app_address):
    if app_name in known_apps:
        #TODO
        print("TODO")
    else:
        print("special app search not implemented for app: ", app_name)
        process_app_data(app_name, app_address)
        

def process_app_media(app_name, media_address):
    if app_name in known_apps:
        #TODO
        print("TODO")
    else:
        print("special media search not implemented for app: ", app_name)



def process_network_data(pcap_address, out_dir):
    start(pcap_address, out_dir)





###################################################################################
def create_extensions():
    with open("analyze/extensions.txt") as file:
        for line in file:
            tmp=line.split(":")
            for x in tmp[1].split(' '):
                ext.update({x:tmp[0]})       

def copy_file(src, dest):
    try:
        
        shutil.copy2(src, dest)
        # print(f"File '{src}' copied successfully to '{dest}'")

    except Exception as e:
        print(f"Error copying file: {e}")


def extension_org(address,out):
    for item in ext_list:
        dir = os.path.join(out, "extension", item)
        if not os.path.exists(dir):
            print(f"Directory '{dir}' does not exist. Creating it now.")
            os.makedirs(dir)

    for root, dirs, files in os.walk(address):
        for file in files:
            full_name=os.path.join(root, file)
            _, file_extension = os.path.splitext(full_name)
            file_type = ext.get(file_extension[1:])
            with open("{output}/extension/ts.txt".format(output=out), "a") as ts:
                if (file_type is not None):
                    dest=os.path.join(out, "extension", file_type, full_name.replace('/', '_'))
                    copy_file(full_name, dest)
                    ts.write("{name} {mtime}\n".format(name=full_name, mtime=os.path.getmtime(full_name)))
                    
                else:
                    dest=os.path.join(out, "extension", "others", full_name.replace('/', '_'))
                    copy_file(full_name, dest)
                    ts.write("{name} {mtime}\n".format(name=full_name, mtime=os.path.getmtime(full_name)))


def face_analyze(img_address, face_address):
    image_utils.start_face_process(img_address, face_address)



    

# address = "out/data_tmp"
# out="out/analyze"
# img_address = "out/analyze/extension/image"
# face_address = "out/analyze/faces"

# j=0
# img = cv2.imread("/home/alireza/university/master/final-project/code/Android-Forensic-Framework/out/analyze/extension/image/out_data_tmp_sdcard_Android_data_ir.eitaa.messenger_cache_1_101052.jpg")
# f=utils.extract_faces(img, "retinaface")
# if (f is None):
#     print("no face found")
# for face in f:
#     j+=1
#     area = face['facial_area']
#     x = area['x']
#     y = area['y']   
#     w = area['w']
#     h = area['h']      
#     crop_img = img[y:y+h, x:x+w]
#     name = "face-{j}-{im}.jpg".format(j=j, im="img")
#     cv2.imwrite(name, crop_img)
# start(address, out, img_address, face_address)