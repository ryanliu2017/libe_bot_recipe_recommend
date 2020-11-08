from gensim.models import Word2Vec
import time
import numpy as np
from numba import jit
from random import sample,randint
# 套用別人的code，完成詞向量加總平均得到文本向量
from recipe_system.UtilWordEmbedding import MeanEmbeddingVectorizer
import redis

'''
此版本已改寫成從redis取得食譜資訊
裡面function回傳值有修改(get_recipe_info)
'''
'''
    def get_recipe_info(self,user_sim_list):
        for idx,each in enumerate(user_sim_list):
            recipe_id = each[0]
            recipe = self.redis.hgetall(recipe_id)
            recipe_ing_str = recipe["ingredient"]
            recipe_ing = recipe_ing_str.split(",")
            recipe_like = recipe["like"]
            recipe_url = recipe['url']
            recipe_ing_set = set([x.split(" ")[0] for x in recipe_ing])
            yield (recipe["recipe"],recipe_like,recipe_ing_str,recipe_ing_set)
'''



class Recipe_recommender():

    def __init__(self,ip):
        self.model = Word2Vec.load("recipe_system/w2v_recipe.model")
        self.mean_embedding_vec = MeanEmbeddingVectorizer(self.model)
        self.doc_vec = np.loadtxt('recipe_system/doc_vec.csv', delimiter=',')

        self.redis = redis.StrictRedis(host=ip, port=6379, decode_responses=True)

    def __str__(self):
        return "This is a recipe recommender, please put your refrigerator content for augment" \
               " to get your own recommendation."

    # 封裝成function，把用戶所擁有食材轉換成向量, input為食材串列: ["麵粉",'抹茶',"紅豆"]
    def convert_vector(self,user_refri_list: list):
        user_embedding = self.mean_embedding_vec.transform([user_refri_list])
        return user_embedding.reshape(100, )

    def calculate_similarity(self,user_vec: np.ndarray):
        '''setting function to calculate cosine similarity with numba module'''
        @jit(nopython=True)
        def cosine_similarity_numba(u: np.ndarray, v: np.ndarray):
            assert (u.shape[0] == v.shape[0])
            uv = 0
            uu = 0
            vv = 0
            for i in range(u.shape[0]):
                uv += u[i] * v[i]
                uu += u[i] * u[i]
                vv += v[i] * v[i]
            cos_theta = 1
            if uu != 0 and vv != 0:
                cos_theta = uv / np.sqrt(uu * vv)
                return cos_theta
            else:
                return 0

        '''start calculating'''
        cosine_numba = {}
        for idx, vec in enumerate(self.doc_vec):
            cosine_numba[idx] = cosine_similarity_numba(user_vec, vec)

        election_list = sorted(cosine_numba.items(), key=lambda item: item[1], reverse=True)
        '''return only top 10 high similarity recipe'''
        return election_list[:10]

    def get_recipe_info(self, user_sim_list):
        for idx, each in enumerate(user_sim_list):
            recipe_id = each[0]
            recipe = self.redis.hgetall(recipe_id)
            recipe_ing = recipe["ingredient"].split(",")
            recipe_ing_set = set([x.split(" ")[0] for x in recipe_ing])
            recipe["ing_set"] = recipe_ing_set

            yield recipe

    def from_set_to_recipe_list(self,user_set):
        user_vec = self.convert_vector(user_set)
        user_sim_list = self.calculate_similarity(user_vec)
        return list(self.get_recipe_info(user_sim_list))

    def quick_recommend(self,user_refri_list):
        user_set = set(user_refri_list)
        random_set = sample(user_refri_list, randint(2, len(user_refri_list)))
        recom_list = self.from_set_to_recipe_list(random_set)

        waiting_recipe = {}  # 存放待定食譜
        for idx, each_selected in enumerate(recom_list):
            recipe_set = each_selected["ing_set"]
            ing_diff = recipe_set - user_set
            each_selected["diff"] = ing_diff

            if not ing_diff:
                return each_selected

            else:
                if not waiting_recipe:
                    waiting_recipe = each_selected
                    continue
                elif len(waiting_recipe["diff"]) > len(ing_diff):  # 如果該食譜缺漏食材數更少，就把待定食譜換成此食譜
                    waiting_recipe = each_selected
                    continue

        return waiting_recipe

    def refrigerator_cleaner(self,user_refri_list):
        '''
        user_refri_list: 使用者所擁有的所有食材
        doc_vec: 全食譜的食譜向量(numpy array)
        ----------------------------------------------------------
        此方法為持有食材之使用最大化的食譜推薦系統
        步驟分解
        1. 試圖用全部食材組成一向量
        2. 以此向量計算食譜相似度，得到一個以相似度高低排序過的清單
        3. 將清單內的食譜食材一一和用戶擁有食材比對
        4. 如果有完全符合食材需求的食譜就進行推薦
        5. 若無，則推薦缺漏食材數最少的食譜
        6. 推薦完食譜後扣除使用食材，再以剩餘食材組成一向量，重複步驟2-6
        7. 一直推薦到剩餘食材少於2樣時停止推薦
        '''
        selected_number = 1
        elected_recipe = []
        while True:
            user_set = set(user_refri_list)
            if len(user_set) < 2:
                try:
                    print(f'食材不足,只剩下{user_set.pop()},停止提供推薦...')
                    break
                except KeyError:
                    print(f'食材不足,停止提供推薦...')
                    break
            recom_list = self.from_set_to_recipe_list(user_set)

            waiting_recipe = {}  #存放待定食譜
            for idx,each_selected in enumerate(recom_list):
                # each_selected是dictionary
                recipe_set = each_selected["ing_set"]
                ing_diff = recipe_set - user_set
                each_selected["diff"] = ing_diff

                # 判定條件: recipe_set裡面是否有不在user_set內的食材,若無則回傳set(), if判定False
                if not ing_diff:
                    print(f"已為您找到第{selected_number}道食譜: {each_selected['recipe']}")
                    # print(f'所需食材: {recipe_set}')
                    user_refri_list = user_set - recipe_set
                    elected_recipe.append(each_selected)
                    break

                # enter if not full matched
                else:
                    if not waiting_recipe:
                        waiting_recipe = each_selected
                        continue
                    elif len(waiting_recipe["diff"]) > len(ing_diff):    # 如果該食譜缺漏食材數更少，就把待定食譜換成此食譜
                        waiting_recipe = each_selected
                        continue

                # 拜訪完全部食譜，都沒有完全match的
                if idx+1 == len(recom_list):
                    # print(f"已為您找到第{selected_number}道食譜: {waiting_recipe[1]}")
                    # print(f'所需食材: {waiting_recipe[3]}, 有缺食材: {waiting_recipe[-1]}')

                    #扣除食譜食材
                    user_refri_list = user_set - waiting_recipe["ing_set"]
                    elected_recipe.append(waiting_recipe)
                    break
            selected_number += 1

        return elected_recipe

    def recipe_recommend_system(self,user_refri_list,recipe_number=5):
        '''
        user_refri_list: 使用者所擁有的所有食材
        doc_vec: 全食譜的食譜向量(numpy array)
        ----------------------------------------------------------
        recipe_number: 期望推薦的食譜數量，預設為10道
        此方法為從持有食材隨機抽樣進行推薦的系統
        步驟分解
        1. 隨機選出不定數量的食材組合成一向量
        2. 以此向量計算食譜相似度，得到一個以相似度高低排序過的清單
        3. 將清單內的食譜食材一一和用戶擁有食材比對
        4. 如果有完全符合食材需求的食譜就推薦出來，若無就pass
        5. 該清單比對完後進行下一輪，重複步驟1-5
        6. 若連續三輪都找不到完全符合食材需求的食譜，則從次輪開始進入快速推薦
        6-1. 快速推薦: 每一輪必推薦一道食譜，如果有完全符合的則優先，若無則推薦食材缺少數最低的食譜
        7. 直到推薦清單達到設定值後便停止推薦
        '''

        selected_number = 1
        not_found_count = 0
        recommend_recipe_name = set()
        elected_recipe = []
        while True:
            if selected_number == recipe_number + 1:
                # print(f'已完成{recipe_number}道食譜推薦...')
                break

            user_set = set(user_refri_list)
            random_set = sample(user_refri_list,randint(2,len(user_refri_list)))
            recom_list = self.from_set_to_recipe_list(random_set)


            for idx,each_selected in enumerate(recom_list):
                if each_selected["recipe"] in recommend_recipe_name:
                    continue
                recipe_set = each_selected["ing_set"]
                ing_diff = recipe_set - user_set
                each_selected["diff"] = ing_diff

                # 判定條件: recipe_set裡面是否有不在user_set內的食材,若無則回傳set(), if判定False
                if not ing_diff:
                    # print(f"已為您找到第{selected_number}道食譜: {each_selected[1]}")
                    # print(f'所需食材: {recipe_set}')
                    selected_number += 1
                    # not_found_count = 0  # 開啟則是連續條件，不開則是累積條件
                    recommend_recipe_name.add(each_selected["recipe"])
                    elected_recipe.append(each_selected)
                    break
                else:
                    pass

                if idx+1 == len(recom_list):
                    not_found_count += 1


            # 判斷是否進入快速推薦
            if not_found_count >= 3:
                print('累積三次無法推薦完全符合的食譜，進入第二階段快速推薦')
                for i in range(recipe_number-selected_number+1):
                    #　持續找，直到找到沒有重複的食譜
                    while True:
                        quick_recipe = self.quick_recommend(user_refri_list)
                        if quick_recipe["recipe"] not in recommend_recipe_name:
                            break

                    elected_recipe.append(quick_recipe)
                    recommend_recipe_name.add(quick_recipe["recipe"])

                    selected_number += 1

                break

            else:
                continue

        return elected_recipe


def main():

    start = time.time()
    recomm = Recipe_recommender("192.168.1.176")
    end = time.time()
    print(f"Class created,{round(end - start,2)} seconds used.")
    user_refri_list = ["麵粉", '鮮奶油', '雞蛋', '香蕉', '洋蔥', '蝦', '藍苺', '豬肉', '高麗菜', '番茄', '大蒜', '抹茶', "太白粉"]

    first_recom = recomm.refrigerator_cleaner(user_refri_list)
    end1 = time.time()
    print(f"First recommendation,{round(end1 - end, 2)} seconds used.")
    print(first_recom)
    print("---------------------------------------------------------------------")

    start2 = time.time()
    second_recom = recomm.recipe_recommend_system(user_refri_list)
    end2 = time.time()
    print(f"Second recommendation,{round(end2 - start2, 2)} seconds used.")
    print(second_recom)


if __name__ == "__main__":
    main()
