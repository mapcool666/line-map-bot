from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage, LocationMessage,
    QuickReply, QuickReplyButton, MessageAction
)
import requests
import os
from dotenv import load_dotenv
import urllib.parse

load_dotenv()

app = Flask(__name__)

line_bot_api = LineBotApi(os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))
handler = WebhookHandler(os.getenv("LINE_CHANNEL_SECRET"))
GOOGLE_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")

# 暫時記憶每個用戶的起點（部署時可改用資料庫）
user_origins = {}

# 常用起點選項（可自行修改）
quick_origin_options = [
    ("🏠 家", "台中市太平區建功街71號"),
    ("🏢 公司", "台中市西屯區文心路三段"),
    ("🚉 車站", "台中火車站")
]

def get_drive_time(origin, destination):
    url = "https://maps.googleapis.com/maps/api/directions/json"

    params = {
        "origin": origin,
        "destination": destination,
        "key": GOOGLE_API_KEY,
        "mode": "driving",
        "language": "zh-TW",
        "region": "tw",
        "departure_time": "now"
    }

    response = requests.get(url, params=params).json()

    if not response.get('routes'):
        return f"{destination}\n1651黑 🄲代駕\n查詢失敗：找不到路線"

    try:
        leg = response['routes'][0]['legs'][0]
        duration_text = leg.get('duration_in_traffic', {}).get('text')
        if not duration_text:
            duration_text = leg['duration']['text']

        minutes = int(''.join(filter(str.isdigit, duration_text))) + 2

        # 加上 Google Maps 導航連結
        origin_encoded = urllib.parse.quote(origin)
        destination_encoded = urllib.parse.quote(destination)
        map_url = f"https://www.google.com/maps/dir/?api=1&origin={origin_encoded}&destination={destination_encoded}&travelmode=driving"

        return f"{destination}\n1651黑 🄲代駕\n{minutes}分\n\n👉 Google Maps 導航：\n{map_url}"
    except Exception as e:
        return f"{destination}\n1651黑 🄲代駕\n查詢失敗：{str(e)}"

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_text(event):
    user_id = event.source.user_id
    message_text = event.message.text

    # 若使用者點選快速選單設定起點
    for label, origin_text in quick_origin_options:
        if message_text == label:
            user_origins[user_id] = origin_text
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=f"✅ 已將起點設定為「{label}」：{origin_text}")
            )
            return

    if user_id not in user_origins:
        quick_reply = QuickReply(
            items=[
                QuickReplyButton(action=MessageAction(label=label, text=label))
                for label, _ in quick_origin_options
            ]
        )
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(
                text="請先傳送一個「位置訊息」，或選擇常用起點：",
                quick_reply=quick_reply
            )
        )
        return

    origin = user_origins[user_id]
    destination = message_text
    reply = get_drive_time(origin, destination)
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply)
    )

@handler.add(MessageEvent, message=LocationMessage)
def handle_location(event):
    user_id = event.source.user_id
    lat = event.message.latitude
    lng = event.message.longitude
    origin = f"{lat},{lng}"
    user_origins[user_id] = origin

    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text="✅ 已設定目前位置為起點！您可以開始查詢目的地了。")
    )

if __name__ == "__main__":
    app.run()
