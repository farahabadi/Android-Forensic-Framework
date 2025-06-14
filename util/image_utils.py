from deepface import DeepFace
import numpy as np
import cv2
import time
import os
import operator
import pickle
import shutil
from sklearn.cluster import DBSCAN
import json

def find_faces(face, db, model, backend):
    dfs = DeepFace.find(
      img_path = face,
      db_path = db,
      model_name=model,
      detector_backend=backend,
    )
    return dfs


def open_image(path):
    img = cv2.imread(path)
    return img

def extract_faces(img, backend):
    faces = DeepFace.extract_faces(
        img_path = img,
        enforce_detection = False,
        anti_spoofing = True,
        detector_backend=backend
        )
    return faces


# main method
def face_extract(img_address, face_address):
    print("img address: ", img_address)
    # for _, _, files in os.walk(img_address):
    crop_face_and_save(img_address, face_address, limit_size=5000)




def draw_rect_and_save(db, save_address):
    backends = [
      'fastmtcnn',
      'yolov8',
    ]
    for i in range(len(backends)):
        print("\nbackend: ", backends[i])
        for x in os.listdir(db):
            if (not os.path.isfile(os.path.join(db, x))):
                continue
            img = cv2.imread(os.path.join(db, x))
            start = time.time()
            faces = extract_faces(img, backend=backends[i])
            if (faces is None):
                print(x, "  no face found")
                continue
            j=0
            for face in faces:
                j+=1
                area = face['facial_area']
                start_point = (area['x'], area['y'])        
                arrow =  (area['w'], area['h'])        
                end_point =  tuple(map(operator.add, start_point, arrow))        
                color = list(np.random.random(size=3) * 256)
                cv2.rectangle(img, start_point, end_point, color, 2)
            end = time.time()
            print("image: ", x, "    num of faces:", j, "    time: ", end - start)
            name = "{im}-{backend}.jpg".format(backend=backends[i], im=x)
            address = os.path.join(save_address, name)
            cv2.imwrite(address, img)


def crop_face_and_save(db, save_address, limit_size):
    backends = [
      'yolov8',
    ]
    for i in range(len(backends)):
        print("\nbackend: ", backends[i])
        for l in os.listdir(db):
            if (not os.path.isfile(os.path.join(db, l))):
                continue
            if (os.path.getsize(os.path.join(db, l)) < limit_size):
                continue
            img = cv2.imread(os.path.join(db, l))
            faces = extract_faces(img, backend=backends[i])
            if (faces is None):
                print(l, "  no face found")
                continue
            j=0
            for face in faces:
                conf = face['confidence']
                print("confidence: ", conf)
                if (conf < 0.7):
                    continue
                j+=1
                area = face['facial_area']
                x = area['x']
                y = area['y']
                w = area['w']
                h = area['h']      
                crop_img = img[y:y+h, x:x+w]
                name = "face-{j}-{im}-{backend}.jpg".format(j=j, backend=backends[i], im=l)
                print(name)
                address = os.path.join(save_address, name)
                cv2.imwrite(address, crop_img)

##############################3##############################3##############################3##############################3####################


def find_same_identities(face_address, save_path, thresh, same_num):
    id=1
    all_related=[]
    size_limit = 10000
    os.makedirs(save_path, exist_ok=True)
    os.makedirs((save_path + "/others"), exist_ok=True)
    for file in os.listdir(face_address):
        pic = os.path.join(face_address, file)
        ext = os.path.splitext(pic)[-1].lower()
        if (ext == ".jpg" or ext == ".png"):
            if pic in all_related:
                continue
            if (os.path.getsize(pic) < size_limit):
                shutil.copy2(pic, save_path + "/others")
                continue
            same=0
            related=[]
            results = DeepFace.find(img_path=pic, db_path=face_address, detector_backend="yolov8", model_name="ArcFace", enforce_detection="False")
            for df in results:
                for index, row in df.iterrows():
                    if (float(row['distance']) < float(thresh)):
                        # print("row['identiry']", row['identity'])
                        if (os.path.getsize(row['identity']) < size_limit):
                            continue
                        if (row['identity'] in all_related):
                            continue
                        related.append(row['identity'])
                        all_related.append(row['identity'])
                        same +=1
            print("same: ", same)
            if same >= same_num:
                address = save_path + "/identity" + str(id)
                os.makedirs(address, exist_ok=True)
                for file in related:
                    shutil.copy2(file, address)
                shutil.copy2(pic, address)
                id +=1
            else:
                shutil.copy2(pic, save_path + "/others")


def start_face_process(img_address, face_address):
    face_extract(img_address, face_address)
    embd_save_address = face_address + "/embeddings.pkl"
    embeddings = extract_embeddings(face_address, model_name='ArcFace', save_path=embd_save_address)
    identities = cluster_faces_by_identity(embeddings, eps=0.5, min_samples=2)
    output_dir = face_address + "/identities"
    save_identities(identities, output_dir)
    
if __name__ == '__main__':
    # face_extract("projects/proj2/processed_data/extension/image", "projects/proj2/processed_data/faces")
    find_same_identities("projects/proj2/processed_data/faces", "projects/proj2/processed_data/faces/identities", thresh="0.5", same_num=2)
