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
    for _, _, files in os.walk(img_address):
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
                if (conf < 0.5):
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

# main method
def extract_embeddings(face_dir, model_name='ArcFace', save_path='embeddings.pkl'):
    """
    Extract facial embeddings from cropped face images
    """
    if os.path.exists(save_path):
        with open(save_path, 'rb') as f:
            return pickle.load(f)
    
    embeddings = {}
    face_paths = [os.path.join(face_dir, f) for f in os.listdir(face_dir) 
                 if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    
    print(f"Extracting embeddings for {len(face_paths)} faces using {model_name}")
    
    for face_path in face_paths:
        try:
            embedding_obj = DeepFace.represent(
                img_path=face_path,
                model_name=model_name,
                enforce_detection=False
            )
            embedding = embedding_obj[0]["embedding"] if isinstance(embedding_obj, list) else embedding_obj["embedding"]
            embeddings[face_path] = embedding
        except Exception as e:
            print(f"Error processing {face_path}: {str(e)}")
    
    with open(save_path, 'wb') as f:
        pickle.dump(embeddings, f)
    
    return embeddings

# main method

def cluster_faces_by_identity(embeddings, eps=0.4, min_samples=2):
    """
    Cluster face embeddings using DBSCAN algorithm
    """
    face_paths = list(embeddings.keys())
    embedding_matrix = np.array([embeddings[path] for path in face_paths])
    
    # Normalize embeddings for cosine similarity
    embedding_matrix = embedding_matrix / np.linalg.norm(embedding_matrix, axis=1, keepdims=True)
    
    # DBSCAN clustering with cosine distance
    clustering = DBSCAN(eps=eps, min_samples=min_samples, metric='cosine').fit(embedding_matrix)
    labels = clustering.labels_
    
    # Create identity groups
    identities = {}
    for path, label in zip(face_paths, labels):
        identity_id = f"identity_{label}" if label != -1 else f"unknown_{abs(hash(path))}"
        identities.setdefault(identity_id, []).append(path)
    
    print(f"Created {len(identities)} identity clusters")
    return identities


# main method
def save_identities(identities, output_dir='identities'):
    """
    Organize faces into identity-based directory structure
    """
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)
    os.makedirs(output_dir, exist_ok=True)
    
    identity_map = {}
    
    for identity_id, face_paths in identities.items():
        identity_dir = os.path.join(output_dir, identity_id)
        os.makedirs(identity_dir, exist_ok=True)
        
        for face_path in face_paths:
            face_filename = os.path.basename(face_path)
            dest_path = os.path.join(identity_dir, face_filename)
            shutil.copy2(face_path, dest_path)
        
        identity_map[identity_id] = {
            'num_faces': len(face_paths),
            'faces': [os.path.basename(p) for p in face_paths]
        }
    
    # Save metadata
    with open(os.path.join(output_dir, 'identity_metadata.json'), 'w') as f:
        json.dump(identity_map, f, indent=2)
    


def start_face_process(img_address, face_address):
    face_extract(img_address, face_address)
    embeddings = extract_embeddings(face_address, model_name='ArcFace')
    identities = cluster_faces_by_identity(embeddings, eps=0.5, min_samples=3)
    output_dir = face_address + "/identities"
    save_identities(identities, output_dir)
    