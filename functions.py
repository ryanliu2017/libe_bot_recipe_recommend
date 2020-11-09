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

from linebot.models.template import *
import pprint
import copy
from recipe_system.apriori_simplification_revised import *


'''
建立回復訊息專用物件
'''
class ReplyMessager(object):
    '''
    call functions to return the format of send_message which line_bot_api needs
    '''

    '''
    reply.json templates
    '''
    recipe_menu_tmp = json.load(open("素材/recipe_reply/reply.json", encoding='utf-8'))
    recommend_selection_tmp = json.load(open("素材/recommend_selection/reply.json", encoding='utf-8'))
    iot_tmp = json.load(open("素材/iot_reply/reply.json", encoding='utf-8'))
    ingredient_tmp = json.load(open('素材/ingredient_reply/reply.json', encoding="utf-8"))
    set_tmp = json.load(open("素材/set_selection/reply.json", encoding='utf-8'))
    lack_tmp = json.load(open("素材/lack_ingredient_reply/reply.json", encoding='utf-8'))
    storage_selection_tmp = json.load(open("素材/storage_selection/reply.json", encoding='utf-8'))
    storage_confirm_tmp = json.load(open("素材/storage_confirm/reply.json", encoding='utf-8'))
    cluster = {}
    user_choose = {}
    mode = {}
    keyword_mode = {}
    # 防止文字訊息massage event觸發
    default_word_set = {'今晚我要來點',
                        '想來點什麼呢?',
                        '查看冰箱',
                        '進入您的冰箱',
                        '關鍵字搜索',
                        '進入關鍵字搜索',
                        '啟動智能冰箱',
                        '食材資訊是否正確呢?',
                        '請搜尋食譜，例如:三杯雞',
                        '請搜尋食材，例如:雞蛋',
                        "請選擇節慶",
                        "請選擇異國料理",
                        "中秋節相關食譜",
                        "端午節相關食譜",
                        "萬聖節相關食譜",
                        "聖誕節相關食譜",
                        "情人節相關食譜",
                        "過年年菜相關食譜",
                        "元宵節相關食譜",
                        "日式相關食譜",
                        "韓式相關食譜",
                        "您已成功選入食譜，將幫您從智能冰箱中扣除所需食材",
                        "韓式相關食譜",
                        "日式相關食譜",
                        "西班牙相關食譜",
                        "泰式相關食譜",
                        "美式相關食譜",
                        "法式相關食譜",
                        "港式相關食譜",
                        "義式相關食譜",
                        "台灣小吃相關食譜",
                        "客家相關食譜",
                        "請從下方選單重新開始使用本系統",
                        "準備進貢"
                        }

    @classmethod
    def user_store_add(cls, user_id, ing_name):
        if not cls.user_choose.get(user_id, 0):
            cls.user_choose[user_id] = []

        cls.user_choose[user_id].append(ing_name)
        return cls.user_choose[user_id]

    @classmethod
    def user_store_remove(cls,user_id,ing_name):
        # 如果使用者還沒開始選擇食材或者要刪除的食材根本沒被選到就return None
        if (not cls.user_choose.get(user_id,0)) or (ing_name not in cls.user_choose[user_id]):
            return None

        cls.user_choose[user_id].remove(ing_name)
        return cls.user_choose[user_id]

    # 拿到食譜dict修改成客製化後的format,供FlexSendMessage_CarouselContainer所用
    @classmethod
    def customize_recipe(cls, recipe):
        '''
        :param carouse: reply.json
        :param recipe:  dictionary
                        {'ingredient': '綜合核果 300 gram,麥芽 120 gram,雞蛋 60 gram,蔓越莓 50 gram',
                         'recipe': '過年小零嘴牛軋糖',
                         'recipe_id': '123',
                         'seasoning': '砂糖 170 gram,蜂蜜 50 gram,水 60 ml',
                         'cluster': 'cluster6',
                         'image': 'https://imageproxy.icook.network/resize?height=600&nocrop=false&stripmeta=true&type=auto&url=http%3A%2F%2Ftokyo-kitchen.icook.tw.s3.amazonaws.com%2Fuploads%2Frecipe%2Fcover%2F99211%2F0f2ce1865bd45541.jpg&width=800',
                         'like': '719',
                         'url': 'https://icook.tw/recipes/99211',
                         'time': '30分鐘',
                         'quantity': '1'}
        :return: customized reply.json
        '''
        carousel = copy.deepcopy(cls.recipe_menu_tmp)
        while len(recipe)+1 != len(carousel['contents']):
            carousel['contents'].pop(0)

        for idx, each_recipe in enumerate(recipe):
            carousel['contents'][idx]["hero"]["url"] = each_recipe['image']
            carousel['contents'][idx]["body"]["contents"][0]["contents"][1]["text"] = each_recipe['recipe']
            carousel['contents'][idx]["body"]["contents"][1]["contents"][1]["text"] = str(each_recipe['like'])
            carousel['contents'][idx]["body"]["contents"][2]["contents"][1]["text"] = each_recipe["ingredient"].replace(
                ",", "\n")
            carousel['contents'][idx]["footer"]["contents"][0]["action"]["uri"] = each_recipe["url"]
            carousel['contents'][idx]["footer"]["contents"][1]["action"]["data"] += each_recipe["recipe_id"]
            if each_recipe["diff"]:
                lack_tmp = copy.deepcopy(cls.lack_tmp)
                carousel['contents'][idx]["body"]["contents"].append(lack_tmp)
                carousel['contents'][idx]["body"]["contents"][3]["contents"][1]["text"] += ",".join(each_recipe["diff"])
            else:
                pass

        return carousel

    # 拿到含食譜json的list,製作成line_bot_api所需要的FlexSendMessage
    @classmethod
    def menu_reply_message(cls, recipe):
        '''
        :param carousel:
        :param recipe: list contains dictionaries of recipe
        :return: FlexSendMessage
        '''
        reply_template = cls.customize_recipe(recipe)
        return FlexSendMessage(alt_text="hello", contents=CarouselContainer.new_from_json_dict(reply_template))

    @classmethod
    def ingredient_storage_confirm_message(cls,ingredient_name):
        message = copy.deepcopy(cls.storage_confirm_tmp)
        message["template"]["text"] += ingredient_name + " 嗎?"
        message["template"]["actions"][0]["data"] += ingredient_name
        message["template"]["actions"][1]["data"] += ingredient_name
        return message

    '''
    使用者冰箱查看功能以及挑選食材的TemplateSendMessage
    '''
    @classmethod
    def refrigerator_show(cls,user_refri_dict):
        # "10,gram,2020/10/23"  -> ["10","gram","2020/10/23"]
        global carouse_one

        ingredient_tmp = copy.deepcopy(cls.ingredient_tmp)
        # 取得食材的呈現模板
        refri_show_tmp = ingredient_tmp["template"]["columns"]
        # 取得使用者冰箱食材總數
        carouse_number = len(user_refri_dict)

        for key, value in user_refri_dict.items():
            # 依據食材總數調整reply.json的column數量
            if carouse_number > 1:
                carouse_one = copy.deepcopy(refri_show_tmp[0])
                refri_show_tmp.append(carouse_one)
                carouse_number -= 1
            else:
                carouse_one = refri_show_tmp[0]

            carouse_one["title"] = key
            carouse_one["text"] = value
            carouse_one["actions"][0]["text"] += key
            carouse_one["actions"][0]["data"] += key  # 把食材名稱從postback.data中帶入server
            carouse_one["actions"][1]["text"] += key
            carouse_one["actions"][1]["data"] += key

        return TemplateSendMessage.new_from_json_dict(ingredient_tmp)


    '''
    設計使用者選擇食譜分群的QuickReply Message
    '''
    @staticmethod
    def cluster_send():
        cluster_name = ((0,"清爽滋味"),
                   (1,"台灣元素"),
                   (2,"香滷"),
                   (3,"暖心鍋物"),
                   (4,"西式風味"),
                   (5,"滋養健康"),
                   (6,"烘焙點心"))
        def cluster_generate(cluster):
            cluster_button = QuickReplyButton(
                action=PostbackAction(
                    label=f"{cluster[1]}",
                    data=f"cluster={cluster[0]}",
                    text=f"您已選擇{cluster[1]}，常用的食材組合如下，請從中選取一個，我們將為您推薦相關食譜~"
                )
            )
            return cluster_button
        # map後面參數要改成實際上cluster的各個名稱
        cluster_button = map(cluster_generate, [x for x in cluster_name])

        return TextSendMessage(text='請從下面選項選擇一個食譜分類', quick_reply=QuickReply(items=cluster_button))


    '''
    使用者從模型排出的frequent set中選擇其一
    '''
    @classmethod
    def set_reply(cls,cluster_content, user_id, user_refri_dict):
        def apriori_cal(cluster_content, user_choose, user_refri_dict):
            '''
            :param cluster_number: int
            :param user_choose: list
            :param user_refri_dict: dict
            :return:
            '''

            appointed_output = set(user_choose)
            my_refrigerator = set(user_refri_dict.keys())

            total_i_list = get_total_ingredient_in_recipes(cluster_content, appointed_output)
            if total_i_list:
                recommended_fequent_set = get_frequent_set(total_i_list, appointed_output, my_refrigerator)
                return recommended_fequent_set
            else:
                # total_i_list = None 時該做的事
                return []

        user_choose = cls.user_choose[user_id]
        recommended_fequent_set = apriori_cal(cluster_content, user_choose, user_refri_dict)
        set_tmp = copy.deepcopy(cls.set_tmp)
        if recommended_fequent_set:
            for idx, per_fre_set in enumerate(recommended_fequent_set):
                # 調整button數量
                if len(recommended_fequent_set) != 5:
                    while len(recommended_fequent_set) != len(set_tmp["footer"]["contents"]):
                        set_tmp["footer"]["contents"].pop()

                set_tmp["footer"]["contents"][idx]["action"]["label"] = " ".join(per_fre_set[2])
                set_tmp["footer"]["contents"][idx]["action"]["text"] = " ".join(per_fre_set[2])
                set_tmp["footer"]["contents"][idx]["action"]["data"] += " ".join(per_fre_set[2])
            bubbleContainer = BubbleContainer.new_from_json_dict(set_tmp)
            return FlexSendMessage(alt_text="hello", contents=bubbleContainer)
        else:
            print("Empty, delete related selection")
            cls.user_select_delete(user_id)   # 選擇失敗做初始化
            return TextSendMessage(text="很抱歉，您所選的食材組合無合適資訊，無法為您推薦\n請透過冰箱重新選擇一次食材組合")


    '''
    利用使用者所選擇的frequent set找出食譜作為推薦
    '''
    # 最終拿到recipe_id回傳
    @classmethod
    def apriori_recommend_recipe_id(cls,appointed_frequent_set,cluster_content):
        suggested_recipe = get_suggested_recipe(appointed_frequent_set, cluster_content)
        # suggested_recipe -> [recipe_id1,recipe_id2]
        # cls.cluster[user_id] = None  # initialization
        return suggested_recipe

    @classmethod
    def menu_test(cls):
        return FlexSendMessage(alt_text="hello", contents=CarouselContainer.new_from_json_dict(cls.recipe_menu_tmp))

    @classmethod
    def user_select_delete(cls,user_id):
        cls.user_choose[user_id] = []
        cls.cluster[user_id] = []

    @staticmethod
    def quick_reply_select():
        textQuickReplyButton1 = QuickReplyButton(
            action=PostbackAction(
                label="食譜",
                data="keyword=食譜",
                text="請搜尋食譜，例如:三杯雞"
            )
        )
        textQuickReplyButton2 = QuickReplyButton(
            action=PostbackAction(
                label="食材",
                data="keyword=食材",
                text="請搜尋食材，例如:雞蛋"
            )
        )
        textQuickReplyButton3 = QuickReplyButton(
            action=PostbackAction(
                label="節慶",
                data="keyword=節慶",
                text="請選擇節慶"
            )
        )
        textQuickReplyButton4 = QuickReplyButton(
            action=PostbackAction(
                label="異國料理",
                data="keyword=異國料理",
                text="請選擇異國料理"
            )
        )
        quickReplyList = QuickReply(
            items=[textQuickReplyButton1, textQuickReplyButton2, textQuickReplyButton3, textQuickReplyButton4]
        )
        return TextSendMessage(text='請選擇下面選項', quick_reply=quickReplyList)

    @staticmethod
    def quick_reply_festival():
        textQuickReplyButton_moon = QuickReplyButton(
            action=PostbackAction(
                label="中秋節",
                data="keyword=中秋料理",
                text="中秋節相關食譜"
            )
        )
        textQuickReplyButton_dragon = QuickReplyButton(
            action=PostbackAction(
                label="端午節",
                data="keyword=端午包粽",
                text="端午節相關食譜"
            )
        )
        textQuickReplyButton_halloween = QuickReplyButton(
            action=PostbackAction(
                label="萬聖節",
                data="keyword=萬聖節",
                text="萬聖節相關食譜"
            )
        )
        textQuickReplyButton_Merry = QuickReplyButton(
            action=PostbackAction(
                label="聖誕節",
                data="keyword=聖誕大餐",
                text="聖誕節相關食譜"
            )
        )
        textQuickReplyButton_love = QuickReplyButton(
            action=PostbackAction(
                label="情人節",
                data="keyword=情人節",
                text="情人節相關食譜"
            )
        )
        textQuickReplyButton_Lantern = QuickReplyButton(
            action=PostbackAction(
                label="元宵節",
                data="keyword=元宵湯圓",
                text="元宵節相關食譜"
            )
        )
        textQuickReplyButton_newyear = QuickReplyButton(
            action=PostbackAction(
                label="過年年菜",
                data="keyword=年菜",
                text="過年年菜相關食譜"
            )
        )
        ## 設計節慶 QuickReplyButton的List
        quickReplyList_Festival = QuickReply(
            items=[textQuickReplyButton_moon,
                   textQuickReplyButton_dragon,
                   textQuickReplyButton_halloween,
                   textQuickReplyButton_Merry,
                   textQuickReplyButton_love,
                   textQuickReplyButton_Lantern,
                   textQuickReplyButton_newyear]
        )
        return TextSendMessage(text='發送問題給用戶，請用戶回答', quick_reply=quickReplyList_Festival)

    @staticmethod
    def quick_reply_exotic():
        textQuickReplyButton_korea = QuickReplyButton(
            action=PostbackAction(
                label="韓式",
                data="keyword=韓式",
                text="韓式相關食譜"
            )
        )
        textQuickReplyButton_japan = QuickReplyButton(
            action=PostbackAction(
                label="日式",
                data="keyword=日式",
                text="日式相關食譜"
            )
        )
        textQuickReplyButton_tai = QuickReplyButton(
            action=PostbackAction(
                label="泰式",
                data="keyword=泰式",
                text="泰式相關食譜"
            )
        )
        textQuickReplyButton_spain = QuickReplyButton(
            action=PostbackAction(
                label="西班牙",
                data="keyword=西班牙",
                text="西班牙相關食譜"
            )
        )
        textQuickReplyButton_america = QuickReplyButton(
            action=PostbackAction(
                label="美式",
                data="keyword=美式",
                text="美式相關食譜"
            )
        )
        textQuickReplyButton_france = QuickReplyButton(
            action=PostbackAction(
                label="法式",
                data="keyword=法式",
                text="法式相關食譜"
            )
        )
        textQuickReplyButton_hongkong = QuickReplyButton(
            action=PostbackAction(
                label="港式",
                data="keyword=港式",
                text="港式相關食譜"
            )
        )
        textQuickReplyButton_italy = QuickReplyButton(
            action=PostbackAction(
                label="義式",
                data="keyword=義式",
                text="義式相關食譜"
            )
        )
        textQuickReplyButton_taiwan = QuickReplyButton(
            action=PostbackAction(
                label="台灣小吃",
                data="keyword=台灣小吃",
                text="台灣小吃相關食譜"
            )
        )
        textQuickReplyButton_hakka = QuickReplyButton(
            action=PostbackAction(
                label="客家",
                data="keyword=客家",
                text="客家相關食譜"
            )
        )
        ## 設計異國料理 QuickReplyButton的List
        quickReplyList_Country = QuickReply(
            items=[textQuickReplyButton_korea,
                   textQuickReplyButton_japan,
                   textQuickReplyButton_spain,
                   textQuickReplyButton_america,
                   textQuickReplyButton_tai,
                   textQuickReplyButton_france,
                   textQuickReplyButton_hongkong,
                   textQuickReplyButton_italy,
                   textQuickReplyButton_taiwan,
                   textQuickReplyButton_hakka])
        return TextSendMessage(text='發送問題給用戶，請用戶回答', quick_reply=quickReplyList_Country)

def main():

    user_refri_dict = {"蘋果":"1,顆,2020/10/23",
                       "香蕉":"2,根,2020/10/23",
                       "芭樂":"5,個,2020/10/24",
                       "蓮霧":"7,個,2020/10/21",
                       "雞蛋":"3,個,2020/10/24",
                       "番茄":"10,顆,2020/10/24",
                       "豬肉":"200,gram,2020/10/19"}
    user_choose = ["雞蛋","番茄"]
    test = ReplyMessager.refrigerator_show(user_refri_dict)
    pprint.pprint(test)
    print("------------------------------------------------------------")
    pprint.pprint(ReplyMessager.ingredient_tmp)

    pprint.pprint(ReplyMessager.cluster_send())
    test_set = ReplyMessager.set_reply(1,user_choose,user_refri_dict)
    print(test_set)


if __name__ == '__main__':
    main()