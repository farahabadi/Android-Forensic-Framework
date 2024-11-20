import os, sys
from subprocess import call
import shutil
import cv2
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'image')))
import utils

ext_list=["archive", "app", "audio", "book", "code", "exec", "font", "image", "sheet", "slide", "text", "video", "web", "db", "others"]
ext=dict()

def create_extensions():
    with open("analyze/extensions.txt") as file:
        for line in file:
            tmp=line.split(":")
            for x in tmp[1].split(' '):
                ext.update({x:tmp[0]})       

def copy_file(src, dest):
    try:
        
        shutil.copy2(src, dest)
        print(f"File '{src}' copied successfully to '{dest}'")

    except Exception as e:
        print(f"Error copying file: {e}")


def start(address, out, img_address, face_address):
    # organise by extension
    create_extensions()
    extension_org(address, out)

    #face analysis
    # face_analyze(img_address, face_address)

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
            with open("out/analyze/extension/ts.txt", "a") as ts:
                if (file_type is not None):
                    dest=os.path.join(out, "extension", file_type, full_name.replace('/', '_'))
                    copy_file(full_name, dest)
                    ts.write("{name} {mtime}\n".format(name=full_name, mtime=os.path.getmtime(full_name)))
                    
                else:
                    dest=os.path.join(out, "extension", "others", full_name.replace('/', '_'))
                    copy_file(full_name, dest)
                    ts.write("{name} {mtime}\n".format(name=full_name, mtime=os.path.getmtime(full_name)))


def face_analyze(img_address, face_address):
    face_extract(img_address, face_address)


def face_extract(img_address, face_address):
    for _, _, files in os.walk(img_address):
        utils.crop_face_and_save(img_address, face_address, limit_size=5000)
        for file in files:
            full_name = os.path.join(img_address, file)


address = "out/data_tmp"
out="out/analyze"
img_address = "out/analyze/extension/image"
face_address = "out/analyze/faces"

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
start(address, out, img_address, face_address)