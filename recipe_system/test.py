# from .recipe_recommend_function import Recipe_recommender
# from gensim.models import Word2Vec
# import json
# import time
#
# def main():
#     with open(r'dataset/recipe1018_V8.json', 'r')as f:
#         content = json.load(f)
#
#
#     model = Word2Vec.load("w2v_ingredient_only_V2.model")
#
#
#     start = time.time()
#     recomm = Recipe_recommender(content,model)
#     end = time.time()
#     user_refri_list = ["麵粉",'鮮奶油','雞蛋','香蕉','洋蔥','蝦','藍苺','豬肉','高麗菜','番茄','大蒜','抹茶',"太白粉"]
#     first_recom = recomm.refrigerator_cleaner(user_refri_list)
#     end1 = time.time()
#     second_recom = recomm.recipe_recommend_system(user_refri_list)
#     end2 = time.time()
#     print(f"Class created,{round(end - start,2)} seconds used.")
#     print(f"First recommendation,{round(end1 - start, 2)} seconds used.")
#     print(f"Second recommendation,{round(end2 - end1, 2)} seconds used.")
#
#     print(first_recom)
#     print("----------------------------------")
#     print(second_recom)
#
# if __name__ == "__main__":
#     main()

# import timeit
# timeit.timeit('[]', number=10**7)
# timeit.timeit('list()', number=10**7)



from gensim.models import Word2Vec
from random import sample,randint
import pprint
model = Word2Vec.load("w2v_ingredient_only_V2.model")
vocab = list(model.wv.vocab)
print(vocab)

user_refri_list = []
for i in range(10):
    user_refri = {}
    num = randint(3,10)
    ing = sample(vocab,num)
    for j in ing:
        user_refri[j] = f"{randint(10,500)},gram,2020/10/20"
    user_refri_list.append(user_refri)

pprint.pprint(user_refri_list)