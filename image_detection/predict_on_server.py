from tensorflow.keras.models import load_model
import numpy as np
import os
import cv2


class inception_retrain(object):
    def __init__(self):
        self.label = ['香蕉', '高麗菜', '雞蛋', '茄子', '洋蔥', '番茄']
        self.img_path = 'dataset/'
        self.model = load_model('image_detection/inv3_single_furniture_binary_1.h5')
        self.InV3model = load_model("image_detection/inception.h5")
        self.img_size = np.zeros([299, 299, 3]).shape

    def image_process(self,image):
        # 圖片預處理
        arr = np.asarray(bytearray(image), dtype=np.uint8)
        image = cv2.imdecode(arr, -1)
        # 傳進來的原始圖片像素
        self.img_size = image.shape
        image = cv2.resize(image, (299, 299))
        image = np.expand_dims(image/255, axis=0)
        image = np.vstack([image])
        return image

    def model_load(self, img):
        # 載入圖片與模型
        image = self.image_process(img)
        features = self.InV3model.predict(image)
        return features

    def predict(self,img):
        # 傳回圖片屬於各個類別的機率
        image = self.model_load(img)
        pred = self.model.predict(image)
        idx = pred.argmax()
        return self.label[idx], self.img_size


def main():
    num = 0; correct_num = 0
    error_list = []
    inception = inception_retrain()
    for item in os.listdir(inception.img_path):
        error = {}
        # if num == 1: break
        if item[:-6] == inception.predict(item):
            correct_num += 1
        elif item[:-7] == inception.predict(item):
            correct_num += 1
        else:
            error[item] = inception.predict(item)
            error_list.append(error)
    print(correct_num)
    print(error_list)

if __name__ == '__main__':
    # GPU加速
    os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
    main()


# 每種類別各用100張做比對，列出不符合者。

'''
https://blog.gtwang.org/programming/opencv-basic-image-read-and-write-tutorial/
圖片讀取:
img = cv2.imread("dataset/banana1.jpg")
'''