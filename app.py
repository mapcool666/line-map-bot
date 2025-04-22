from urllib.parse import quote
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage, LocationMessage, QuickReply, QuickReplyButton, MessageAction
import requests
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
line_bot_api = LineBotApi(os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))
handler = WebhookHandler(os.getenv("LINE_CHANNEL_SECRET"))

user_states = {}

def get_drive_time(origin, destination):
    url = "https://maps.googleapis.com/maps/api/directions/json"
    params = {
        "origin": origin,
        "destination": destination,
        "departure_time": "now",
        "key": os.getenv("GOOGLE_MAPS_API_KEY")
    }

    response = requests.get(url, params=params).json()

    if not response.get("routes"):
        return f"{destination}\n1651黑 🈲代駕\n查詢失敗：找不到路線", None

    try:
        duration_text = response['routes'][0]['legs'][0]['duration_in_traffic']['text']
        duration_min = int(''.join(filter(str.isdigit, duration_text))) + 2
        return f"{destination}\n1651黑 🈲代駕\n{duration_min}分", destination
    except Exception as e:
        return f"{destination}\n1651黑 🈲代駕\n查詢失敗：{str(e)}", None

@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers["X-Line-Signature"]
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return "OK"

@handler.add(MessageEvent, message=LocationMessage)
def handle_location(event):
    user_id = event.source.user_id
    lat = event.message.latitude
    lng = event.message.longitude
    user_states[user_id] = f"{lat},{lng}"
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text="✅ 已設定目前位置為起點！您可以開始查詢目的地了。")
    )

@handler.add(MessageEvent, message=TextMessage)
def handle_text(event):
    user_id = event.source.user_id
    destination = event.message.text

    if user_id not in user_states:
        quick_reply = QuickReply(items=[
            QuickReplyButton(action=MessageAction(label="使用目前位置", text="使用目前位置"))
        ])
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="❗ 請先傳送一個「位置訊息」設定起點。", quick_reply=quick_reply)
        )
        return

    origin = user_states[user_id]
travel_info, dest_encoded = get_drive_time(origin, destination)

# 如果查不到路線就只回傳一則文字
if not dest_encoded:
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=travel_info)
    )
    return

# 正常回報兩則訊息
nav_link = f"https://www.google.com/maps/dir/?api=1&destination={quote(dest_encoded)}&travelmode=driving"
line_bot_api.reply_message(
    event.reply_token,
    [
        TextSendMessage(text=travel_info),
        TextSendMessage(text=f"👇 點我開始導航\n{nav_link}")
    ]
)


if __name__ == "__main__":
    app.run()
