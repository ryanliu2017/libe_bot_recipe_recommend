from hdfs.client import Client, InsecureClient
import redis
import json
import time

client = InsecureClient("http://192.168.1.176:50070", user='spark')
r = redis.StrictRedis(host='192.168.1.176', port=6379, decode_responses=True)

def main():
    with client.read("/recipe/recipe1023_V9.json")as reader:
        data = json.load(reader)

    with client.read("/recipe/tags.txt")as reader:
        tag = reader.read().decode("utf-8")

    print("have got all of data from hdfs!")

    tags = set(tag.split(","))

    start = time.time()
    # push to Redis
    for idx, each in enumerate(data):
        _id = each["_id"]

        # tags-key sorted set
        tag_set = set(each["tags"])
        # tags是從網站分類抓下來的104種分類
        for one_tag in tag_set & tags:
            r.zadd(one_tag, {_id: each["like"]})

        # ingredient-key sorted set
        for one_ing in each["ing_dict"].keys():
            r.zadd(one_ing, {_id: each["like"]})

        # recipe name and _id insert into a sorted set
        r.zadd("recipe_name",{f"{_id},{each['recipe']}": each["like"]})

        global ingredient_str
        ingredient_str = ""
        # recipe hash table, _id: key
        if each["ingredient"]:
            for ing in each["ingredient"]:
                ing_str = ing[0] + " " + str(ing[1]) + " " + str(ing[2])    # ["雞蛋",1,"顆"] -> "雞蛋 1 顆"
                ingredient_str += ing_str + ","

        global seasoning_str
        seasoning_str = ""
        if each["seasoning"]:
            for sea in each["seasoning"]:
                sea_str = sea[0] + " " + str(sea[1]) + " " + str(sea[2])
                seasoning_str += sea_str + ","

        value = {"recipe": each["recipe"],
                 "recipe_id": _id,
                 "url": each["url"],
                 "image": each["image"],
                 "like": each["like"],
                 "cluster": each["cluster"],
                 "ingredient": ingredient_str[:-1],
                 "seasoning": seasoning_str[:-1],
                 "quantity": each["quantity"],
                 "time": each["time"]}

        cluster_value = {_id: ingredient_str + str(each["like"])}

        r.hmset(_id, value)
        r.hmset(each["cluster"], cluster_value)


        if idx % 10000 == 0:
            print(f"Have uploaded {idx+1} data.")


    #     print(value)
    end = time.time()
    print(f"{end - start} sec used.")
    print(f"total {len(r.keys())} keys created.")

if __name__ == "__main__":
    main()

