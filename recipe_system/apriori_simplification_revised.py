import json
from mlxtend.preprocessing import TransactionEncoder
import pandas as pd
from mlxtend.frequent_patterns import apriori
import time

def get_total_recipes(cluster,path="./dataset/"):
    with open(path + f'recipe1023_cluster{cluster}.json','r')as f:
        content = json.load(f)
    return content

def get_total_ingredient_in_recipes(content,appointed_output):
    total_i_list = []
    for each_recipe in content:
        each_i_list = []
        if appointed_output.issubset(set(each_recipe['ing_dict'])):
                for each_i in each_recipe['ing_dict']:
                    each_i_list.append(each_i)
                    #print(each_i_list)
                total_i_list.append(each_i_list)
    if len(total_i_list) > 10:
        return total_i_list
    else:
        print('此類別無指定frequent set,請重新指定食材')
        return []


def get_frequent_set(total_i_list, appointed_output, my_refrigerator):
    def set_giver(sort_set_list: list):
        recommended_fequent_set = []

        for r_num in range(1, 5):
            recommended_name = []
            for num, i in enumerate(sort_set_list):
                if r_num == 1:
                    # if 判斷反著寫，不符合的就進入continue
                    if not ((appointed_output.issubset(i)) and (i.issubset(my_refrigerator))):
                        continue
                elif r_num == 2:
                    if not ((appointed_output.issubset(i)) and (round(sort_set.iloc[num, 0], 3) > 0.3)):
                        continue
                elif r_num == 3:
                    if not i.issubset(my_refrigerator):
                        continue
                else:
                    pass

                # 只有通過前面考驗的set會被append
                '''
                i: 關聯配對
                i & my_refrigerator - appointed_output: 找出的配對有除了input以外的其他食材(冰箱內的)
                i - my_refrigerator: 配對中有使用者沒有的
                appointed_output - i:提供的配對有非input的食材
                '''
                set_info = [sort_set.index[num], round(sort_set.iloc[num, 0], 3), i,
                            i & my_refrigerator - appointed_output, i - my_refrigerator, appointed_output - i,r_num]
                recommended_fequent_set.append(set_info)
                recommended_name.append(i)

                # 湊齊5個就回傳
                if len(recommended_fequent_set) == 5:
                    return recommended_fequent_set

            for selected_set in recommended_name:
                sort_set_list.remove(selected_set)

        # 不管最後找到幾個結果都回傳
        return recommended_fequent_set

    te = TransactionEncoder()
    te_ary = te.fit(total_i_list).transform(total_i_list)
    df = pd.DataFrame(te_ary, columns=te.columns_)
    frequent_itemsets = apriori(df, min_support=0.1, use_colnames=True)
    if frequent_itemsets["itemsets"].count() < 2:
        frequent_itemsets = apriori(df, min_support=1/(df.count()[0]-1), use_colnames=True)
    # print(f"{frequent_itemsets.count()}")
    frequent_itemsets['length'] = frequent_itemsets['itemsets'].apply(lambda x: len(x))
    output_set = frequent_itemsets[(frequent_itemsets['length'] >= len(appointed_output) + 1)]
    # print(output_set.count())
    sort_set = output_set.sort_values(['support'], ascending=False)

    recommended_fequent_set = set_giver(sort_set['itemsets'].tolist())

    return recommended_fequent_set

def get_suggested_recipe(appointed_frequent_set,content):
    appointed_recipe_list = []
    like_dic = dict()
    for each_recipe in content:
        if appointed_frequent_set.issubset(set(each_recipe['ing_dict'])):
        # if appointed_frequent_set[2].issubset(set(each_recipe['ing_dict'])):
            like_dic[each_recipe['_id']] = int(each_recipe['like'])

    election_list = sorted(like_dic.items(),key=lambda item: item[1],reverse=True)


    for index,value in enumerate(election_list[:5]):
        each_id = value[0]
        #print(each_id)
        for each_recipe in content:
            if each_id == each_recipe['_id']:
                # API用
                appointed_recipe_list.append(each_recipe["_id"])
                # 測試用
                # appointed_recipe_list.append([each_recipe['_id'],each_recipe['recipe'],each_recipe['like'],each_recipe['ingredient'],each_recipe['seasoning'],each_recipe['cluster']])
    return appointed_recipe_list

'''
使用者需要輸入冰箱食材、指定食材配對、食譜cluster、以及選擇計算後得到的frequent set選項
'''
def main():

    start = time.time()

    my_refrigerator = {'番茄','雞蛋','九層塔','蘋果','高麗菜','茄子','紅蘿蔔','香菇'}
    appointed_output = {'九層塔'} #need user to choose
    cluster = 3  #need user to choose


    content = get_total_recipes(cluster)
    total_i_list = get_total_ingredient_in_recipes(content,appointed_output)
    print(total_i_list)
    if total_i_list:
        recommended_fequent_set = get_frequent_set(total_i_list,appointed_output,my_refrigerator)
        appointed_frequent_set = recommended_fequent_set[4]  #need user to choose
        suggested_recipe = get_suggested_recipe(appointed_frequent_set,content)
        print(appointed_frequent_set)
        for idx, each_set in enumerate(recommended_fequent_set):
            print(f"{idx}. frequent_set: {each_set[2]}, support: {each_set[1]},{each_set[6]} round")
            print(f"搭配您冰箱內的:{each_set[3]}")
            if each_set[4]:
                print(f"推薦您購買:{each_set[4]}")
            if each_set[5]:
                print(f"缺少您指定食材:{each_set[5]}")
            print("==========================================================")

        print(suggested_recipe)
    else:
        # total_i_list = None 時該做的事
        print("Empty.")
    end = time.time()
    print(f"{end-start} sec used.")

if __name__ == "__main__":
    main()