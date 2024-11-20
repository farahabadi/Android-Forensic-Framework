from deepface import DeepFace
import numpy as np
import cv2
import time
import os
import operator

def extract_faces():
    #TODO
    return null


def save_faces(loc):
    #TODO
    return null

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