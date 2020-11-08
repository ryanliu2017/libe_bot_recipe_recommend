from tensorflow.keras.models import load_model
import numpy as np
import os
import cv2


class inception_retrain(object):
    def __init__(self):
        self.label = ['banana', 'cabbage', 'egg', 'eggplant', 'onion', 'tomato']
        self.img_path = 'dataset/'
        self.model = load_model('image_detection/inv3_single_furniture_binary_1.h5')
        self.InV3model = load_model("image_detection/inception.h5")

    def image_process(self,img):
        # 圖片預處理
        image = cv2.imread(self.img_path + img)
        print(f"image process in cv2.imdecode,size: {image.shape}, data: {image}")
        image = cv2.resize(image, (299, 299))
        # print(f"image process in cv2.resize,size: {image.shape}, data: {image}")
        image = np.expand_dims(image/255, axis=0)
        # print(f"image process in np.expand_dims,size: {image.shape}, data: {image}")
        image = np.vstack([image])
        # print(f"image process in np.stack,size: {image.shape}, data: {image}")
        print("--------------------------------------------------------------")
        return image

    def model_load(self, img):
        # 載入圖片與模型
        image = self.image_process(img)
        print(f"model load, image shape: {image.shape}")
        features = self.InV3model.predict(image)
        print(f"features: {features}")
        print("--------------------------------------------------------------")
        return features

    def predict(self,img):
        # 傳回圖片屬於各個類別的機率
        image = self.model_load(img)
        pred=self.model.predict(image)
        print(f"fitted model predict: {pred}")
        pred=np.round(pred,3).reshape(6,)
        print(f"predict reshape: {pred}")
        return pred[0],pred[1],pred[2],pred[3],pred[4],pred[5]

    def result_check(self,img):
        # 找出正確值得標籤
        pred_list = list()
        pred0,pred1,pred2,pred3,pred4,pred5 = self.predict(img)
        pred_list.append(pred0); pred_list.append(pred1); pred_list.append(pred2)
        pred_list.append(pred3); pred_list.append(pred4); pred_list.append(pred5)
        print(pred_list)
        return self.label[pred_list.index(max(pred_list))] #取得a最大的index


def main():
    num = 0; correct_num = 0
    error_list = []
    inception = inception_retrain()
    for item in os.listdir(inception.img_path):
        error = {}
        # if num == 1: break
        if item[:-6] == inception.result_check(item):
            correct_num += 1
        elif item[:-7] == inception.result_check(item):
            correct_num += 1
        else:
            error[item] = inception.result_check(item)
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