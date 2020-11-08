import pymysql
import json
'''
用於清空MySQL資料庫使用者資訊
'''

ip_info = json.load(open("./ip_info.json", 'r', encoding='utf8'))

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


def main():
    db = 'recipe'
    conn = connect_to_mysql(db)
    cursor = conn.cursor()

    sql_1 = '''
    SET FOREIGN_KEY_CHECKS = 0;
    '''

    cursor.execute(sql_1)
    conn.commit()

    sql_2 = '''
    truncate user_profile;
    '''

    cursor.execute(sql_2)
    conn.commit()


    sql_3 = '''
    SET FOREIGN_KEY_CHECKS = 1;
    '''

    cursor.executemany(sql_3)
    conn.commit()

    cursor.close()
    conn.close()

if __name__ == '__main__':
    main()