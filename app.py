from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage, LocationMessage
import requests
import os
from dotenv import load_dotenv
from urllib.parse import quote

load_dotenv()

app = Flask(__name__)

line_bot_api = LineBotApi(os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))
handler = WebhookHandler(os.getenv("LINE_CHANNEL_SECRET"))
GOOGLE_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")

# 儲存目前的起點位置
user_origin = {}

def get_drive_time(user_id, destination):
    origin = user_origin.get(user_id)
    if not origin:
        return "❗ 請先傳送位置訊息，或使用快速選單設定起點。"

    url = "https://maps.googleapis.com/maps/api/directions/json"
    params = {
        "origin": origin,
        "destination": destination,
        "mode": "driving",
        "departure_time": "now",
        "key": GOOGLE_API_KEY
    }

    response = requests.get(url, params=params).json()

    if not response.get("routes"):
        return f"{destination}\n1651黑 🈲代駕\n查詢失敗：找不到路線"

    try:
        duration = response['routes'][0]['legs'][0]['duration_in_traffic']['text']
        duration = duration.replace(" 分鐘", "").replace("分鐘", "").replace(" 分", "").replace("分", "")
        duration = str(int(duration) + 2)  # 加 2 分鐘

        reply_text = f"{destination}\n1651黑 🈲代駕\n{duration}分"

        # 將 destination 做 URL encode，避免中文網址錯誤
        encoded_destination = quote(destination)
        maps_url = f"https://www.google.com/maps/dir/?api=1&destination={encoded_destination}&travelmode=driving"
        maps_reply = f"👇 點我開始導航\n{maps_url}"

        return [TextSendMessage(text=reply_text), TextSendMessage(text=maps_reply)]
    except Exception as e:
        return [TextSendMessage(text=f"{destination}\n1651黑 🈲代駕\n查詢失敗：{str(e)}")]

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK'

@handler.add(MessageEvent, message=LocationMessage)
def handle_location(event):
    lat = event.message.latitude
    lng = event.message.longitude
    user_id = event.source.user_id
    user_origin[user_id] = f"{lat},{lng}"
    reply = "✅ 已設定目前位置為起點！您可以開始查詢目的地了。"
    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))

@handler.add(MessageEvent, message=TextMessage)
def handle_text(event):
    user_id = event.source.user_id
    destination = event.message.text
    result = get_drive_time(user_id, destination)
    if isinstance(result, list):
        line_bot_api.reply_message(event.reply_token, result)
    else:
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=result))

if __name__ == "__main__":
    app.run()
