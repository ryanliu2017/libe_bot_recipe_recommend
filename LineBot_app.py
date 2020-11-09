# 引用Web Server套件
from flask import Flask, request, abort, render_template
# 從linebot 套件包裡引用 LineBotApi 與 WebhookHandler 類別
from linebot import (
    LineBotApi, WebhookHandler
)
# 引用無效簽章錯誤
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import (
    ImagemapSendMessage,
    TextSendMessage,
    ImageSendMessage,
    LocationSendMessage,
    FlexSendMessage,
    VideoSendMessage,
    StickerSendMessage,
    AudioSendMessage,
    CarouselContainer,
    BubbleContainer,
    MessageAction,
    URIAction,
    PostbackAction,
    DatetimePickerAction,
    CameraAction,
    CameraRollAction,
    LocationAction,
    QuickReply,
    QuickReplyButton
)
from linebot.models import FollowEvent, PostbackEvent, MessageEvent, TextMessage, TextSendMessage, ImageSendMessage, \
    ImageMessage
from linebot.models.template import *
import json
from urllib.parse import parse_qs
import paramiko
# 自己寫的API
from functions import ReplyMessager
from user_db_api import DataBaseConnector
# recommendation model
from recipe_system.recipe_recommend_function_redis import Recipe_recommender
# 圖像辨識
from image_detection.predict_on_server import inception_retrain

secretFileContentJson = json.load(open("./line_secret_key.json", 'r', encoding='utf8'))

app = Flask(__name__, static_url_path="/素材", static_folder="./素材/", template_folder="./素材/template")

line_bot_api = LineBotApi(secretFileContentJson.get("channel_access_token"))

handler = WebhookHandler(secretFileContentJson.get("secret_key"))
# ssh connection for iot
ssh_client = paramiko.SSHClient()
# 允許連線不在know_hosts檔案中的主機
ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

ip_info = json.load(open("./ip_info.json", 'r', encoding='utf8'))
# database connect
db = DataBaseConnector(ip_info.get("HDFS"))
recommender = Recipe_recommender(ip_info.get("Redis"))
image_model = inception_retrain()


def recommend(event, user_refri_dict, mode=None):
    '''
    :param event:
    :param user_refri_dict:
    :param mode: clean or random
    :return:
    suggested_recipe: dictionary
    '''
    user_refri_list = list(user_refri_dict.keys())
    global suggested_recipe
    if mode == "clean":
        suggested_recipe = recommender.refrigerator_cleaner(user_refri_list)
    elif mode == "random":
        suggested_recipe = recommender.recipe_recommend_system(user_refri_list)

    send_message = ReplyMessager.menu_reply_message(suggested_recipe)
    line_bot_api.reply_message(event.reply_token, send_message)


def recipe_recommendation_message(event, recipe_id):
    '''
    :param event: line_api send the event
    :param reply_token: reply_token
    :param recipe_id: [id1,id2,id3,id4,id5]
    :return: None, 最終直接透過line api傳回食譜清單
    調入使用者冰箱資料，檢查每個推薦食譜的使用食材對於使用者是否有缺
    '''
    recipe = db.get_multi_recipe_from_id(recipe_id)
    user_id = event.source.user_id
    user_refri_dict = db.get_user_refrigerator(user_id)
    user_set = set(user_refri_dict.keys())

    # check full match or partial
    for each in recipe:
        ing_set = set(x.split(" ")[0] for x in each["ingredient"].split(","))
        if ing_set - user_set:
            each["diff"] = ing_set - user_set
        else:
            each["diff"] = set()

    send_message = ReplyMessager.menu_reply_message(recipe)
    return send_message
    # line_bot_api.reply_message(event.reply_token, send_message)


def reply_from_tag(event, tag):
    recipe_list = db.select_tag_redis(tag)
    return recipe_recommendation_message(event, recipe_list)


@app.route("/", methods=['GET'])
def hello():
    return "Hello"


# 問卷訪問網址
@app.route("/survey", methods=['GET', 'POST'])
def survey():
    print(request)
    print(request.values)
    print(request.args)
    print(request.form)
    print(request.values["user_ID"])
    if request.method == "POST":
        profile = {
            "account": request.values.get("Account"),
            "password": request.values.get("Password"),
            "line_user_id": request.values.get("user_ID"),
            "user_name": request.values.get("UserName"),
            "email": request.values.get("UserMail"),
            "phone": request.values.get("Phone"),
            "gender": request.values.get("gender"),
            "age": request.values.get("age"),
            "taste": request.values.getlist("taste"),
            "style": request.values.getlist("taste1"),
            "priority": request.values.getlist("taste2"),
            "other": request.values.get("OtherPriority"),
            "dislike_ingredient": request.values.get("dislike_ingredient")
        }
        print(profile)

        if profile["account"] in db.redis.hvals("total_user_id"):
            return "很抱歉，帳號已註冊，請重新輸入新的帳號"

        # 寫入MySQL
        if db.create_user_mysql(profile):
            pass
        else:
            return "MySQL Writing Error"
        # 從MySQL寫入Redis
        if db.new_user_from_mysql_to_redis(profile["line_user_id"]):
            pass
        else:
            line_bot_api.push_message(
                profile["line_user_id"],
                TextSendMessage(text='很抱歉，系統異常\n請稍後再次填寫一次問卷\n萬分抱歉!!')
            )

        return 'Hello ' + request.values.get('user_ID')
    return render_template("generic.html", ID=request.values["user_ID"])

# 設計給consumer的路徑
@app.route("/kafka_consumer", methods=['POST'])
def kafka():
    image_dict = {"onion1": "洋蔥",
                  "banana1": "香蕉",
                  "eggplant1": "茄子",
                  "tomato1": "番茄",
                  "cabbage1": "高麗菜",
                  "egg1": "雞蛋"}
    if request.values:
        print(request.values)
        user_id = request.values.get("user_id")
        ingredient_name = request.values.get("food_name")
        ingredient_name = image_dict[ingredient_name]
        quantity = request.values.get("food_weight")
        print(f"user_id: {user_id}")
        print(f"ingredient: {ingredient_name}, {quantity}")
        ingredient_str = f"{ingredient_name} {quantity} g"

        ingredient_name = db.user_enter_storage(ingredient_str, user_id)
        if ingredient_name:
            line_bot_api.push_message(
                user_id, TemplateSendMessage.new_from_json_dict(ReplyMessager.ingredient_storage_confirm_message(ingredient_name))
            )
            return f"{user_id}, you have successfully post data to server."
        else:
            return f"{user_id}, you fail to post data to server."

    else:
        return "Please visit the url with data"


# 啟動server對外接口，使Line能丟消息進來
@app.route("/callback", methods=['POST'])
def callback():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']

    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK'


@handler.add(FollowEvent)
def process_follow_event(event):
    # 使用者綁定設定的richmenu
    line_bot_api.link_rich_menu_to_user(event.source.user_id, "richmenu-c19737c2877e07d16e98ceb9e2af077f")
    user_profile = line_bot_api.get_profile(event.source.user_id)
    print(user_profile)
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=f'{user_profile.display_name} 您好！歡迎來到食在，想不到\n請點擊下方圖文選單!')
    )

    if db.check_user_exist(event.source.user_id):
        pass
    else:
        line_bot_api.push_message(
            event.source.user_id,
            [TextSendMessage(text='由於您是新使用者\n建議先從下方連結問卷\n填寫您的口味偏好及帳號註冊\n以利為您服務!'),
             TextSendMessage(text=f'問卷連結: https://2a061328ab21.ap.ngrok.io/survey?user_ID={event.source.user_id}')]
        )


'''
postback key
menu: 從圖文選單點選進入
refri: 從冰箱點選進入
cluster: 使用者選擇分群結果
keyword: 從關鍵字搜索-節慶選擇進入
confirm: 使用者食譜點選確認進入
frequentset: 使用者選擇的食材組合
cancel:使用者不滿意當前的推薦食譜
recom: 使用者從今晚我想來點..進入
input: 食材進貢方式
ing_confirm: 食材進貢後資料正確性的確認
'''


@handler.add(PostbackEvent)
def process_postback_event(event):
    # print(event)
    # print(event.postback.data)
    user_id = event.source.user_id
    user_refri_dict = db.get_user_refrigerator(user_id)
    ReplyMessager.mode[user_id] = False
    ReplyMessager.keyword_mode[user_id] = 0

    pb_data = parse_qs(event.postback.data)
    pb_function, action = list(pb_data.items())[0]
    print(pb_function, action[0])
    if pb_function == "menu":
        print("enter to menu:")
        if action[0] == '今晚我要來點':
            line_bot_api.reply_message(
                event.reply_token,
                [TextSendMessage(text="想來點什麼呢?"),
                 TemplateSendMessage.new_from_json_dict(ReplyMessager.recommend_selection_tmp)]
            )
        elif action[0] == '查看冰箱':
            if not user_refri_dict:
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text="很抱歉查無相關資料，請連結您的智能冰箱新增食材"))
            else:
                line_bot_api.reply_message(
                    event.reply_token,
                    [TextSendMessage(text="進入您的冰箱"),
                     ReplyMessager.refrigerator_show(user_refri_dict),
                     TextSendMessage(text="您可以從冰箱中選取數個種類不同的食材\n"
                                          "讓我來為您介紹相關的食材搭配以及食譜推薦!\n\n"
                                          "點選完畢請輸入 ok")]
                )
        elif action[0] == '關鍵字搜索':
            line_bot_api.reply_message(
                event.reply_token,
                ReplyMessager.quick_reply_select()
            )
        elif action[0] == '準備進貢':
            line_bot_api.reply_message(
                event.reply_token,
                TemplateSendMessage.new_from_json_dict(ReplyMessager.storage_selection_tmp)
            )
    elif pb_function == "input":
        if action[0] == "manual":
            ReplyMessager.mode[user_id] = True
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=f"請開始進貢\n食材輸入方式範例: '牛肉 200 g'"))
        elif action[0] == "iot":
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="為您連線中請稍後...")
            )
            try:
                ssh_client.connect(hostname=ip_info.get("ResberryPi"), port=22, username='pi', password='123')
                line_bot_api.push_message(
                    user_id,
                    TextSendMessage(text="已建立連線請開始操作...")
                )

                stdin, stdout, stderr = ssh_client.exec_command(f"/usr/bin/python3 /home/pi/hx711py/Project/control_v2.py {user_id}")
                # stdin, stdout, stderr = ssh_client.exec_command(f"/usr/bin/python3 /home/pi/hx711py/Project/example1.py")
                res = stdout.read().decode('utf-8')
                print(res)
                line_bot_api.push_message(
                    user_id,
                    TextSendMessage(text="response get.")
                )
                ssh_client.close()
            except Exception as e:
                print(e)

    elif pb_function == "refri":
        # action[0] -> "1,蘋果"
        op_action, ing_name = action[0].split(",")
        if op_action == '1':
            print("加入選擇")
            update_list = ReplyMessager.user_store_add(user_id, ing_name)
            print(update_list)
            pass
        elif op_action == '0':
            print("移除中")
            update_list = ReplyMessager.user_store_remove(user_id, ing_name)
            if not update_list:
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text="很抱歉\n食材未在清單上\n刪除失敗"))
            print(update_list)
            pass
    elif pb_function == "cluster":
        # 從postback拿到分群選擇，再到redis撈該群食譜資料做計算
        cluster_number = int(action[0][0])
        ReplyMessager.cluster[user_id] = cluster_number
        cluster_content = db.cluster_content_get(cluster_number)
        line_bot_api.reply_message(
            event.reply_token,
            ReplyMessager.set_reply(cluster_content, user_id, user_refri_dict)
        )
    elif pb_function == "frequentset":
        appointed_frequent_set = set(action[0].split(" "))
        print(appointed_frequent_set)
        # 將使用者選的set傳回取得要推薦的recipe id
        cluster_content = db.cluster_content_get(ReplyMessager.cluster[user_id])
        suggested_recipe_id = ReplyMessager.apriori_recommend_recipe_id(appointed_frequent_set, cluster_content)
        print(suggested_recipe_id)
        line_bot_api.reply_message(
            event.reply_token,
            [TextSendMessage(text=f"以下為您推薦該組合相關的熱門食譜"),
             recipe_recommendation_message(event, suggested_recipe_id)])
    elif pb_function == "keyword":
        if action[0] == '食譜':
            ReplyMessager.keyword_mode[user_id] = 1
        elif action[0] == '食材':
            ReplyMessager.keyword_mode[user_id] = 2
        elif action[0] == '節慶':
            line_bot_api.reply_message(
                event.reply_token,
                ReplyMessager.quick_reply_festival()
            )
        elif action[0] == '異國料理':
            line_bot_api.reply_message(
                event.reply_token,
                ReplyMessager.quick_reply_exotic()
            )
        else:
            line_bot_api.reply_message(
                event.reply_token,
                reply_from_tag(event, action[0])
            )
    elif pb_function == "confirm":
        recipe_id = action[0]
        if db.get_user_refrigerator(user_id):
            ReplyMessager.user_select_delete(user_id)
            db.menu_select(user_id, recipe_id)
            lack = db.lack[user_id]
            if lack:
                line_bot_api.push_message(user_id, TextSendMessage(text=f"提醒您\n記得購買 {','.join(lack)} 喔"))
        else:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="很抱歉，請先新增您冰箱的食材資訊\n以利為您提供更多服務")
            )
        '''連線資料庫扣除使用食材'''
    elif pb_function == "cancel":
        ReplyMessager.user_select_delete(user_id)
        pass
        '''可能做些初始化動作'''
    elif pb_function == "recom":
        if len(db.get_user_refrigerator(user_id)) > 1:
            recommend(event, user_refri_dict, mode=action[0])
        else:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="很抱歉，請先新增您冰箱的食材資訊\n以利為您提供更多服務")
            )
    elif pb_function == "ing_confirm":
        ReplyMessager.mode[user_id] = True
        confirm, ingredient = action[0].split(",")
        # 輸入資訊正確
        if int(confirm):
            reply = TextSendMessage(text=f"已完成 {ingredient} 進貢\n請繼續輸入欲進貢的食材\n如欲結束請輸入'進貢結束'")
        else:
            if db.user_delete_storage(user_id,ingredient):
                pass
            else:
                print("系統異常，無法刪除新增的食材")
            reply = TextSendMessage(text=f"{ingredient} 進貢失敗!!!\n請確認格式並重新輸入欲進貢的食材\n如欲結束請輸入'進貢結束'")

        line_bot_api.reply_message(
            event.reply_token,
            reply)



@handler.add(MessageEvent, message=TextMessage)
def process_text_message(event):
    # print("message event:",event)
    text = event.message.text
    user_id = event.source.user_id
    try:
        # 判斷輸入文字內容是否為stopWords
        if event.message.text in ReplyMessager.default_word_set:
            pass
        # 改變進貢狀態
        elif text == "進貢結束":
            ReplyMessager.mode[user_id] = False
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=f"進貢結束\n請繼續使用本服務"))
        # 判斷輸入文字階段是否為進貢狀態
        elif ReplyMessager.mode[user_id]:
            ingredient_name = db.user_enter_storage(text, user_id)
            if ingredient_name:
                line_bot_api.reply_message(
                    event.reply_token,
                    TemplateSendMessage.new_from_json_dict(ReplyMessager.ingredient_storage_confirm_message(ingredient_name))
                )
            else:
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text=f"{text} 進貢失敗!!!\n請確認格式並重新輸入欲進貢的食材\n如欲結束請輸入'進貢結束'"))
        # 輪播食譜選單測試
        elif text.lower() == "0":
            line_bot_api.reply_message(event.reply_token, ReplyMessager.menu_test())

        elif text.lower() == "order":
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="您目前已經選擇了: " + ",".join(ReplyMessager.user_choose[user_id]))
            )
        # 使用者選擇完食材要進行下一步
        elif text.lower() == "ok":
            try:
                user_choose = ReplyMessager.user_choose[user_id]
                print(f"in message: {user_choose}")
                if user_choose:
                    line_bot_api.reply_message(
                        event.reply_token,
                        [TextSendMessage(text="您最後選擇了: " + ",".join(user_choose)), ReplyMessager.cluster_send()])
                else:
                    print("Nothing choosed.")
                    line_bot_api.reply_message(
                        event.reply_token,
                        TextSendMessage(text="你沒選擇任何食材，無法為您推薦"))
            except KeyError:
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text="你沒選擇任何食材，無法為您推薦"))

            # (0,[('52144,烤雞炒飯', 92.0), ('119827,心太軟紅棗糯米', 25.0)]
            # 這部分做食譜的關鍵字搜索
        # 食譜關鍵字查詢狀態
        elif ReplyMessager.keyword_mode[user_id] == 1:
            catch_recipe = db.redis.zscan("recipe_name", 0, f"*{text}*", 180000)
            # 檢查看有無搜索到
            if catch_recipe[1]:
                election_list = sorted(catch_recipe[1], key=lambda x: x[1], reverse=True)[:5]
                recipe_id_list = []
                for i in election_list:
                    get_recipe_id = i[0].split(',')[0]
                    recipe_id_list.append(get_recipe_id)
                line_bot_api.reply_message(
                    event.reply_token,
                    [TextSendMessage(text=f"以下為您推薦與 {text} 相關的熱門食譜"),
                     recipe_recommendation_message(event, recipe_id_list)])
            else:
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text="查無相關食譜，請重新使用服務"))
            # 結束後重設為關閉，必須從關鍵字檢索進入
            ReplyMessager.keyword_mode[user_id] = 0
        # 食材關鍵字查詢
        elif ReplyMessager.keyword_mode[user_id] == 2:
            # check if input text is the same as the default word of ingredient
            if db.redis.hexists("general_ingredient", text):
                reply = reply_from_tag(event, text)
            elif db.redis.hget("synonym", text):
                reply = reply_from_tag(event, db.redis.hget("synonym", text))
            else:
                reply = TextSendMessage(text="查無相關食譜，請重新使用服務")
            line_bot_api.reply_message(
                event.reply_token,
                reply
            )
            ReplyMessager.keyword_mode[user_id] = 0

    except Exception as e:
        print(e)
        pass


@handler.add(MessageEvent, message=ImageMessage)
def handle_image_message(event):
    print(event)
    message_content = line_bot_api.get_message_content(event.message.id)
    # 使用模型api進行辨識
    image_detection_result = image_model.predict(message_content.content)
    image_name, image_size = image_detection_result
    print(f"image has sent to local, the size is : {image_size}, the result is {image_name}")


    # 回復辨識結果
    line_bot_api.reply_message(
        event.reply_token,
        [TextSendMessage(text=f"您剛才上傳的圖片為 {image_name}"),
         TextSendMessage(text=f"以下為您推薦該食材相關的熱門食譜:"),
         reply_from_tag(event, image_name)])

    # 圖片拉回本地端
    file_path = "image_detection/dataset/" + image_name + "_" + event.message.id + '.jpg'
    with open(file_path, 'wb') as fd:
        for chunk in message_content.iter_content():
            fd.write(chunk)


if __name__ == "__main__":
    # 開啟網頁
    app.run(host='0.0.0.0', debug=True)

# import os
# if __name__ == "__main__":
#     app.run(host='0.0.0.0', port=os.environ['PORT'])
