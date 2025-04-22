from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import (
    MessageEvent, TextMessage, LocationMessage,
    TextSendMessage
)
import requests
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

line_bot_api = LineBotApi(os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))
handler = WebhookHandler(os.getenv("LINE_CHANNEL_SECRET"))
GOOGLE_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")

# 記憶使用者起點（位置字典）
user_origin_map = {}

# 回傳常用起點提示
def origin_required_message():
    return TextSendMessage(
        text="請先傳送一個「位置訊息」，或選擇常用起點：\n🏠 家、🏢 公司、🚉 車站"
    )

# 查詢時間主功能
def get_drive_time(destination):
    # 這版導航連結不需要 origin，使用者手機位置當作起點
    url = "https://maps.googleapis.com/maps/api/directions/json"

    # 對 Google 查詢時仍使用假設起點，僅用於預估時間
    origin_for_api = "台中市西屯區逢明街29巷70號"

    params = {
        "origin": origin_for_api,
        "destination": destination,
        "key": GOOGLE_API_KEY,
        "mode": "driving",
        "language": "zh-TW",
        "region": "tw",
        "departure_time": "now"
    }

    response = requests.get(url, params=params).json()

    if not response.get('routes'):
        return f"{destination}\n1651黑 🈲代駕\n查詢失敗：找不到路線", None

    try:
        leg = response['routes'][0]['legs'][0]
        duration_text = leg.get('duration_in_traffic', {}).get('text') or leg['duration']['text']
        minutes = int(''.join(filter(str.isdigit, duration_text))) + 2

        # 導航連結不帶 origin（使用者手機即時定位）
        maps_link = f"https://www.google.com/maps/dir/?api=1&destination={destination}&travelmode=driving"

        return f"{destination}\n1651黑 🈲代駕\n{minutes}分", maps_link
    except Exception as e:
        return f"{destination}\n1651黑 🈲代駕\n查詢失敗：{str(e)}", None

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

# 處理文字訊息（查目的地）
@handler.add(MessageEvent, message=TextMessage)
def handle_text(event):
    user_id = event.source.user_id
    user_text = event.message.text

    # 若尚未設定起點 → 提示設定
    if user_id not in user_origin_map:
        line_bot_api.reply_message(event.reply_token, origin_required_message())
        return

    reply_text, maps_link = get_drive_time(user_text)

    messages = [TextSendMessage(text=reply_text)]
    if maps_link:
        messages.append(TextSendMessage(text=f"👇 點我開始導航\n{maps_link}"))

    line_bot_api.reply_message(event.reply_token, messages)

# 處理位置訊息（設定起點）
@handler.add(MessageEvent, message=LocationMessage)
def handle_location(event):
    user_id = event.source.user_id
    location = event.message.address or f"{event.message.latitude},{event.message.longitude}"
    user_origin_map[user_id] = location

    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text="✅ 已設定目前位置為起點！您可以開始查詢目的地了。")
    )
