from linebot import (
    LineBotApi, WebhookHandler
)
from linebot.models import RichMenu
import requests
import json


secretFileContentJson=json.load(open("./line_secret_key",'r',encoding="utf-8"))

print(secretFileContentJson.get("channel_access_token"))
print(secretFileContentJson.get("secret_key"))
print(secretFileContentJson.get("self_user_id"))


line_bot_api = LineBotApi(secretFileContentJson.get("channel_access_token"))


'''
菜單設定檔
    設定圖面大小、按鍵名與功能
'''

menuRawData ='''
{
  "size": {
    "width": 2500,
    "height": 1686
  },
  "selected": true,
  "name": "圖文選單 1",
  "chatBarText": "查看更多資訊",
  "areas": [
    {
      "bounds": {
        "x": 153,
        "y": 72,
        "width": 2220,
        "height": 453
      },
      "action": {
        "type": "uri",
        "uri": "https://www.google.com.tw/"
      }
    },
    {
      "bounds": {
        "x": 165,
        "y": 576,
        "width": 513,
        "height": 797
      },
      "action": {
        "type": "postback",
        "text": "查看冰箱",
        "data": "menu=查看冰箱"
      }
    },
    {
      "bounds": {
        "x": 763,
        "y": 593,
        "width": 495,
        "height": 797
      },
      "action": {
        "type": "postback",
        "text": "關鍵字搜索",
        "data": "menu=關鍵字搜索"
      }
    },
    {
      "bounds": {
        "x": 1305,
        "y": 606,
        "width": 517,
        "height": 788
      },
      "action": {
        "type": "postback",
        "text": "今晚我要來點",
        "data": "menu=今晚我要來點"
      }
    },
    {
      "bounds": {
        "x": 1864,
        "y": 602,
        "width": 517,
        "height": 788
      },
      "action": {
        "type": "postback",
        "text": "準備進貢",
        "data": "menu=準備進貢"
      }
    }
  ]
}
'''

'''
載入前面的圖文選單設定，
    並要求line_bot_api將圖文選單上傳至Line
'''

menuJson=json.loads(menuRawData)
lineRichMenuId = line_bot_api.create_rich_menu(RichMenu.new_from_json_dict(menuJson))
print(lineRichMenuId)

'''
將先前準備的菜單照片，以Post消息寄發給Line
    載入照片
    要求line_bot_api，將圖片傳到先前的圖文選單id
'''

uploadImageFile=open("./素材/images/richmenu.jpg",'rb')

setImageResponse = line_bot_api.set_rich_menu_image(lineRichMenuId,'image/jpeg',uploadImageFile)

print(setImageResponse)

'''
將選單綁定到特定用戶身上
    取出上面得到的菜單Id及用戶id
    要求line_bot_api告知Line，將用戶與圖文選單做綁定
'''
# https://api.line.me/v2/bot/user/{userId}/richmenu/{richMenuId}


linkResult=line_bot_api.link_rich_menu_to_user(secretFileContentJson["self_user_id"], lineRichMenuId)
#
print(linkResult)

'''
檢視用戶目前所綁定的菜單
    取出用戶id，並告知line_bot_api，
    line_bot_api傳回用戶所綁定的菜單
    印出
'''

#  https://api.line.me/v2/bot/user/{userId}/richmenu


rich_menu_id = line_bot_api.get_rich_menu_id_of_user(secretFileContentJson["self_user_id"])
print(rich_menu_id)

'''
檢視帳號內，有哪些選單
    要求line_bot_api，向line查詢我方的圖文選單列表
    打印
'''

# rich_menu_list = line_bot_api.get_rich_menu_list()
# print(rich_menu_list[0])
# for rich_menu in rich_menu_list:
#     print(rich_menu.rich_menu_id)
    # if rich_menu.rich_menu_id != "richmenu-92cb4416e528ed5129757a2975da99ff":
    #     line_bot_api.delete_rich_menu(rich_menu.rich_menu_id)



'''
解除選單與特定用戶的綁定
    取出用戶id，並告知line_bot_api，
    line_bot_api解除用戶所綁定的菜單
'''

# lineUnregisterUserMenuResponse=line_bot_api.unlink_rich_menu_from_user(secretFileContentJson["self_user_id"])
# print(lineUnregisterUserMenuResponse)