import customtkinter
from views import welcome
from image import utils
import cv2
import operator
import numpy as np
import time
import os

# app = welcome.WelcomePage()
# app.mainloop()
backends = [
  # 'fast mtcnn',
  'yolov8',
]

models = [
  # "VGG-Face",
  "Facenet",
  "Facenet512", 
  # "OpenFace", 
  # "DeepFace", 
  # "DeepID", 
  # "ArcFace", 
  # "SFace",
  # "GhostFaceNet",
]

img = utils.open_image("/home/alireza/university/master/final-project/code/datasets/1/test2.jpg")

for i in range(len(models)):
    for j in range(len(backends)):
      print("model: ", models[i], "    backend: ", backends[j])
      similars = utils.find_faces(face=img, db="/home/alireza/university/master/final-project/code/datasets/1/res", model=models[i], backend=backends[j])
      for k in similars:
         for l in k['identity']:
            print(l)





# similars = utils.find_faces(face=img, db="/home/alireza/university/master/final-project/code/datasets/", model="OpenFace", backend="fastmtcnn")
# for i in similars:
#     print(i, "th number")
#     print(i.identity)


# db="/home/alireza/university/master/final-project/code/datasets"
# s="/home/alireza/university/master/final-project/code/datasets/1/res"
# utils.crop_face_and_save(db, s)




# cv2.namedWindow('s1', cv2.WINDOW_NORMAL)
# cv2.imshow("s1" ,img)
# cv2.waitKey(0)    # cv2.imwrite("/home/alireza/university/master/final-project/code/datasets/my-images/faces/{num}.jpg".format(num=i), img  )