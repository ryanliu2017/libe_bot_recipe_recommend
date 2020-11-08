from user_db_api import DataBaseConnector


'''
將MySQL資料load進Redis

MySQL最終將在Redis建構3個基本key-value以及數個以使用者Line ID為key的hash
"synonym" , data type: hash
"general_ingredient" , data type: hash
"total_user_id" , data type: hash
"U429ec102b46a5332b32c4f1a8b3b04db" (line_user_id) , data type: hash

'''


def ingredient_load(db):
    # 從mysql同義詞庫抓同義詞存進redis (格式hash-  synonym(key)- {總詞彙(sub key):定義食材(value)
    sql = """
    SELECT s.總食材名稱,i.食材名稱 FROM synonym s JOIN ingredient i ON s.食材ID = i.食材ID;
    """
    # 從mysql抓食材存進redis (格式sort-  general_ingredient:定義食材
    sql2 = """
    SELECT 食材ID, 食材名稱 FROM ingredient;
    """

    db.cursor.execute(sql)
    synonym_redis = db.cursor.fetchall()
    db.cursor.execute(sql2)
    ingredient_redis = db.cursor.fetchall()

    meaning_dict = dict()
    for each in synonym_redis:
        meaning_dict[each[0]] = each[1]
    db.redis.hmset('synonym', meaning_dict)

    food_dict = dict()
    for each in ingredient_redis:
        food_dict[each[1]] = each[0]
    db.redis.hmset('general_ingredient', food_dict)


def user_id_table(db):
    sql = '''
    SELECT `使用者ID`, `Line_ID` from recipe.user_profile;'''
    db.cursor.execute(sql)
    user_info = db.cursor.fetchall()
    # (('Ryan', 'U429ec102b46a5332b32c4f1a8b3b04db'),)

    user_table = {}
    for user in user_info:
        user_table[user[1]] = user[0]
    db.redis.hmset("total_user_id", user_table)


def user_data_load(db):
    # 抓全部冰箱資料
    sql = '''
    SELECT us.Line_ID, ing.食材名稱, re.食材重量, re.食材單位, re.食材存放日, re.食材到期日 
    FROM refrigerator_record re JOIN ingredient ing JOIN user_profile us
    ON re.食材ID = ing.食材ID AND re.使用者ID = us.使用者ID
    WHERE (re.食材取用日 is null);
    '''
    db.cursor.execute(sql)
    refrigerator_record = db.cursor.fetchall()

    if refrigerator_record:
        for row in refrigerator_record:
            ingredient_name = row[1]
            ingredient_info = str(row[2]) + "," + row[3] + "," + str(row[4])
            db.redis.hset(row[0], ingredient_name, ingredient_info)


def main():
    db = DataBaseConnector()

    try:
        ingredient_load(db)
    except Exception as e:
        print(f"ingredient_load failed, Error: {e}")
    try:
        user_id_table(db)
    except Exception as e:
        print(f"user_id_table failed, Error: {e}")
    try:
        user_data_load(db)
    except Exception as e:
        print(f"user_data_load failed, Error: {e}")

    db.cursor.close()
    db.mysql.close()
    print("MySQL loaded data to Redis successfully.")

if __name__ == '__main__':
    main()
