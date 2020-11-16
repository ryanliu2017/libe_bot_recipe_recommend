import re
from datetime import date
import redis
import pymysql
import random
import json
'''
Redis architecture

---------mysql----------------------------------------------------------------------------------------------

user_set (check) key -> set ---> ***set(user_pool,user_id)***

user refrigerator hash -> keys -> values --> hmset(name,key,value) ---> ***hmset(user_id,{ingredient: quantity})***

---------hadoop----------------------------------------------------------------------------------------------

tags and ingredients key -> sorted set --> zadd(name,element,score) ---> ***zadd(tag,{_id:like score})***

recipe hash -> keys -> values --> hmset(name,key,value) ---> ***hmset(_id,{recipeName: recipe,
                                                                           ingredient: "por 150 gram, ..."
                                                                           ...})***
'''

ip_info = json.load(open("./ip_info.json", 'r', encoding='utf8'))


# 統一窗口
class DataBaseConnector(object):
    # 初始化設定
    def __init__(self, ip=ip_info.get("Redis")):
        self.redis = redis.StrictRedis(host=ip, port=6379, decode_responses=True)
        self.mysql = self.connect_to_mysql('recipe')
        self.cursor = self.mysql.cursor()
        self.refrigerator = {}
        self.lack = {}
        self.intersection = {}

    def __str__(self):
        return "It's a db connector for Redis and MySQL to make any changes made from line bot."

    @staticmethod
    def connect_to_mysql(db_name):
        host = ip_info.get("MySQL")
        port = 3306
        user = 'recipe'
        passwd = 'recipe'
        db = db_name
        charset = 'utf8mb4'
        conn = pymysql.connect(host=host, port=port, user=user, passwd=passwd, db=db, charset=charset)
        print('Successfully connected to MySQL : {} !'.format(db_name))
        return conn

    def close_connect_to_mysql(self):
        self.cursor.close()
        self.mysql.close()

    def select_tag_redis(self, tag):
        # 回傳like值由高到低的前五名recipe_id list --> ['38795', '133193', '42584', '37543', '34872']
        # 直接送回排序前五的食譜
        # return self.redis.zrange(tag, 0, 4, desc=True)
        # 這個是隨機選5個發出去
        return random.sample(self.redis.zrange(tag, 0, -1), 5)

    def select_multi_tag_redis(self, tags: list):
        # 回傳多個tag找出的recipe_id交集
        new_key = "_".join(tags)
        self.redis.zinterstore(new_key, tags, aggregate="max")

        return self.redis.zrange(new_key, 0, 4, desc=True)

    def get_recipe_from_id(self, recipe_id):
        return self.redis.hgetall(recipe_id)

    def get_multi_recipe_from_id(self, recipe_id_list):
        return_list = []
        for each in recipe_id_list:
            return_list.append(self.redis.hgetall(each))

        return return_list

    def get_user_refrigerator(self, user_id):
        # return {} if not exist
        return self.redis.hgetall(user_id)

    def check_user_exist(self, user_id):
        # return True or False
        return self.redis.hexists("total_user_id", user_id)

    def create_user_mysql(self, profile):
        '''
        將問卷內容新增至MySQL以及新增user_id到Redis中
        :param profile:{
            "account": request.values.get("Account"),
            "password": request.values.get("Password"),
            "line_user_id": request.values.get("user_ID"),
            "user_name": request.values.get("UserName"),
            "email": request.values.get("UserMail"),
            "phone": request.values.get("Phone"),
            "gender": request.values.get("gender"),
            "age_range": request.values.get("age"),
            "taste": request.values.getlist("taste"),
            "style": request.values.getlist("taste1"),
            "priority": request.values.getlist("taste2"),
            "other": request.values.get("OtherPriority"),
            "dislike_ingredient": request.values.get("dislike_ingredient")
        }
        :return:
        '''
        taste_dict = {'sweet': 1,
                      'salty': 2,
                      'bitter': 3,
                      'spicy': 4,
                      'sour': 5,
                      'Japanese': 6,
                      'Taiwanese': 7,
                      'Chinese': 8,
                      'Korean': 9,
                      'Southeast': 10,
                      'American': 11,
                      'European': 12,
                      'British': 13,
                      'Cheap': 14,
                      'Easy': 15,
                      'DependOther': 16,
                      'Taste': 17}

        try:
            self.mysql = self.connect_to_mysql('recipe')
            self.cursor = self.mysql.cursor()
            sql_to_profile = """
                INSERT INTO user_profile (使用者ID,密碼,Line_ID,姓名,email,性別,電話,生日)  
                VALUES ('{account}','{password}' ,'{line_user_id}', '{user_name}', '{email}', '{gender}', '{phone}', '{age}');
                """.format(**profile)
            self.cursor.execute(sql_to_profile)
            self.mysql.commit()

            # 紀錄用戶偏好於同一張表中
            taste_record = profile["taste"] + profile["style"] + profile["priority"]
            for taste in taste_record:
                sql_to_my_own_preference = """
                    INSERT INTO my_own_prefernece (使用者ID,偏好ID)
                    VALUES ('{}', '{}');
                    """.format(profile["account"], taste_dict[taste])
                self.cursor.execute(sql_to_my_own_preference)
                self.mysql.commit()

            self.close_connect_to_mysql()
            return True
        except Exception as e:
            print(e)
            return False

    def new_user_from_mysql_to_redis(self, user_id):
        # 當使用者輸入完問卷後觸發此method，將剛輸入資料的使用者ID引入redis
        try:
            self.mysql = self.connect_to_mysql('recipe')
            self.cursor = self.mysql.cursor()
            user_add_sql = '''
            SELECT `使用者ID`, `Line_ID` from recipe.user_profile where `Line_ID` = '{}';
            '''.format(user_id)
            self.cursor.execute(user_add_sql)
            user_info = self.cursor.fetchall()[0]
            self.close_connect_to_mysql()
            print(user_info)
            # user_info: ('user6', 'U51051d8f36a42aca6a507da9f7312abf')
            self.redis.hset('total_user_id', user_info[1], user_info[0])
            return True
        except Exception as e:
            print(e)
            return False

    def get_db_userid(self, user_id):
        return self.redis.hget('total_user_id', user_id)

    def menu_select(self, user_id, recipe_id):
        # 使用者點選菜單確認後，觸發此method，將使用者現有食材更新取用紀錄、新增缺少食材紀錄
        self.lack[user_id] = {}
        self.intersection[user_id] = {}

        """移除食材"""
        # 取得食譜使用的食材
        ingredient_list = self.redis.hget(recipe_id, "ingredient").split(",")
        ingredient_set = set(i.split(" ")[0] for i in ingredient_list)
        # 取得使用者冰箱食材準備做交集
        user_set = set(self.redis.hkeys(user_id))
        # 取得兩者共有的食材
        intersection = ingredient_set & user_set
        self.intersection[user_id] = intersection

        # 如果發現使用者完全沒有任何相關食材就return False 不讓使用者點選該食譜
        if not self.intersection[user_id]:
            return False

        # MySQL update 食材取用日期
        # 重新建立連線
        self.mysql = self.connect_to_mysql('recipe')
        self.cursor = self.mysql.cursor()
        today = str(date.today())
        db_id = self.get_db_userid(user_id)  # 從line_id中找user_id
        food_id = self.redis.hmget('general_ingredient', *intersection)

        # 每一食材id: mysql 更新
        for each_ing_id in food_id:
            sql = """
            UPDATE refrigerator_record SET 食材取用日 = "{}" WHERE 使用者ID = "{}" AND 食材ID = "{}";
            """.format(today, db_id, each_ing_id)
            self.cursor.execute(sql)
            self.mysql.commit()

        # 食譜紀錄增加
        sql_my_recipe_record = """                   
        INSERT INTO my_recipe_record (使用者ID, 食譜ID, 食譜使用日期) 
        VALUES ('{}', '{}', '{}');
        """.format(db_id, recipe_id, today)
        self.cursor.execute(sql_my_recipe_record)
        self.mysql.commit()

        #使用者缺漏食材
        lack = ingredient_set - user_set
        self.lack[user_id] = lack

        # 缺漏食材紀錄新增
        if self.lack[user_id]:
            lack_food_id = self.redis.hmget('general_ingredient', *lack)
            for each_lack in lack_food_id:
                sql_lack = """
                INSERT INTO ingredient_lack_record (使用者ID, 食材ID, 食譜ID, 食譜使用日期) 
                VALUES ('{}', '{}', '{}', '{}');
                """.format(db_id, each_lack, recipe_id, today)
                self.cursor.execute(sql_lack)
                self.mysql.commit()

        self.refresh_refrigerator_redis_single(user_id, db_id)

        self.close_connect_to_mysql()

        return True

    def cluster_content_get(self, cluster_number):
        # 食譜K-means分群結果取出
        cluster_content = self.redis.hgetall(f"cluster{cluster_number}")
        _list = []
        for key, value in cluster_content.items():
            _dict = {}
            ingredient = [x.split(" ")[0] for x in value.split(",")[:-1]]
            like = value.split(",")[-1]
            _dict["ing_dict"] = ingredient
            _dict["_id"] = key
            _dict["like"] = like

            _list.append(_dict)

        return _list

    def ingredient_storage(self, food_data, user_id):
        # 實際連資料庫做食材資料新增
        self.mysql = self.connect_to_mysql('recipe')
        self.cursor = self.mysql.cursor()
        today = str(date.today())
        db_id = self.get_db_userid(user_id)  # 從line_id中找user_id

        # 查詢食材名稱對應的id及保存期限
        ing_sql = '''
        select * from recipe.ingredient where `食材名稱` = '{}';
        '''.format(food_data[0])
        self.cursor.execute(ing_sql)
        ing_info = self.cursor.fetchall()
        ing_id, ing_name, expire_date = ing_info[0]
        pattern = r"([\D]*)([\d]+)"
        ex_day_number = re.match(pattern, expire_date).group(2)  # int

        # 新增食材資訊寫入mysql
        sql = """
        INSERT INTO refrigerator_record (使用者ID, 食材ID, 食材重量, 食材單位, 食材存放日, 食材到期日)
        VALUES ('{}', '{}', '{}', '{}', '{}', '{}' + interval '{}' day);
        """.format(db_id, food_data[3], food_data[1], food_data[2], today, today, ex_day_number)

        self.cursor.execute(sql)
        self.mysql.commit()

        # Redis 同步更新
        self.refresh_refrigerator_redis_single(user_id, db_id)

        self.close_connect_to_mysql()

        # self.redis.hset(user_id, food_data[0], food_data[1] + ',' + food_data[2] + ',' + today)
        # print(f"user: {user_id}, update refrigerator success! ({food_data})")

    def ingredient_name_check(self, ingredient_str):
        '''
        該方法用於辨識用戶輸入的食材名稱是否正確且能在同義詞庫查詢到
        :param ingredient_str: '壽司飯 200 g'
        :return: 名稱確認，如果有在定義的同義詞內就回傳正確的名稱資訊，若無就回None
        '''

        food_data = ingredient_str.split()  # ['壽司飯', '200', 'g']
        if not self.redis.hexists("general_ingredient", food_data[0]):  # 如果未在general食材的話,換成general食材
            food_data[0] = self.redis.hget('synonym', food_data[0])
            if food_data[0]:
                pass
            else:
                return None
        food_data.append(self.redis.hget('general_ingredient', food_data[0]))  # 查出食材ID
        return food_data  # ["飯","200","gram","1"]

    def user_enter_storage(self, ingredient_str, user_id):
        # 用戶食材儲存
        food_data = self.ingredient_name_check(ingredient_str)
        if not food_data:
            return False
        else:
            try:
                self.ingredient_storage(food_data, user_id)
            except Exception as e:
                print(e)
                return False
            # 若成功，將最後存取的食材名稱回傳，供linebot做訊息確認使用
            return food_data[0]

    def user_delete_storage(self, user_id, ingredient):
        # 輸入食材辨識錯誤或輸入錯誤，須刪除該資料
        try:
            self.mysql = self.connect_to_mysql('recipe')
            self.cursor = self.mysql.cursor()

            db_id = self.get_db_userid(user_id)  # 從line_id中找user_id
            ingredient_id = self.redis.hget('general_ingredient', ingredient)  # 查食材ID

            del_sql = '''
            DELETE FROM refrigerator_record WHERE (食材ID = '{}' and 使用者ID = '{}');
            '''.format(ingredient_id, db_id)

            self.cursor.execute(del_sql)
            self.mysql.commit()

            self.refresh_refrigerator_redis_single(user_id, db_id)

            self.close_connect_to_mysql()
        except Exception as e:
            print(e)
            return False

        return True

    def refresh_refrigerator_redis_single(self, user_id, db_id=None):
        # 用於單一使用者的冰箱資料更新(從MySQL到Redis)

        if db_id is None:
            db_id = self.get_db_userid(user_id)

        # 抓特定使用者冰箱資料
        sql = '''
        SELECT us.Line_ID, ing.食材名稱, re.食材重量, re.食材單位, re.食材存放日, re.食材到期日 
        FROM refrigerator_record re JOIN ingredient ing JOIN user_profile us
        ON re.食材ID = ing.食材ID AND re.使用者ID = us.使用者ID
        WHERE (re.使用者ID = '{}' AND re.食材取用日 is null);
        '''.format(db_id)
        self.cursor.execute(sql)
        result = self.cursor.fetchall()
        if result:
            # 先將該使用者redis冰箱清除
            self.redis.delete(user_id)
            # 逐項冰箱食材更新進redis
            for row in result:
                # 確認資料正確性
                if user_id == row[0]:
                    ingredient_name = row[1]
                    ingredient_info = str(row[2]) + "," + row[3] + "," + str(row[4])
                    self.redis.hset(user_id, ingredient_name, ingredient_info)
                else:
                    print(f"user_id error, {user_id} and {row[0]}")
                    pass
        else:
            print(f"{user_id} 冰箱沒有紀錄，無法更新")


def main():
    r = redis.StrictRedis(host=ip_info.get("Redis"), port=6379, decode_responses=True)


if __name__ == '__main__':
    main()
