from urllib.parse import quote
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage,
    LocationMessage
)
import requests
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
line_bot_api = LineBotApi(os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))
handler = WebhookHandler(os.getenv("LINE_CHANNEL_SECRET"))

user_states = {}

GOOGLE_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")

# 🔹 從輸入文字中萃取斜線後的查詢字串
def extract_query(text):
    if "/" in text:
        return text.split("/")[-1].strip()
    return text.strip()

# 地點解析（回傳：formatted_address + 精確座標）
def resolve_place(query):
    url = "https://maps.googleapis.com/maps/api/place/findplacefromtext/json"
    params = {
        "input": query,
        "inputtype": "textquery",
        "fields": "formatted_address,geometry",
        "language": "zh-TW",
        "region": "tw",
        "locationbias": "circle:30000@24.1477,120.6736",  # 台中市中心座標，半徑 30 公里
        "key": GOOGLE_API_KEY
    }
    response = requests.get(url, params=params).json()
    candidates = response.get("candidates")
    if candidates:
        location = candidates[0]["geometry"]["location"]
        formatted_address = candidates[0]["formatted_address"]
        return query, f"{location['lat']},{location['lng']}"
    return query, None  # fallback：保留原始輸入名稱

# 查詢開車時間（顯示 display_name 作為名稱）
def get_drive_time(origin, destination_coords, display_name):
    url = "https://maps.googleapis.com/maps/api/directions/json"
    params = {
        "origin": origin,
        "destination": destination_coords,
        "departure_time": "now",
        "key": GOOGLE_API_KEY,
        "mode": "driving",
        "language": "zh-TW",
        "region": "tw"
    }

    response = requests.get(url, params=params).json()

    if not response.get("routes"):
        return f"{display_name}\n1651黑 🈲代駕\n查詢失敗：找不到路線", None

    try:
        seconds = response["routes"][0]["legs"][0]["duration_in_traffic"]["value"]
        minutes = int(seconds / 60) + 2
        return f"{display_name}\n1651黑 🈲代駕\n{minutes}分", destination_coords
    except Exception as e:
        return f"{display_name}\n1651黑 🈲代駕\n查詢失敗：{str(e)}", None

@app.route("/callback", methods=["GET", "POST"])
def callback():
    if request.method == "GET":
        return "✅ LINE bot 正常運作", 200  # for UptimeRobot health check

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
    raw_query = event.message.text  # 使用者輸入原文
    search_query = extract_query(raw_query)  # 萃取關鍵字查詢用

    if user_id not in user_states:
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="❗ 請先傳送一個「位置訊息」設定起點。")
        )
        return

    origin = user_states[user_id]
    display_name, destination_coords = resolve_place(search_query)

    if not destination_coords:
        destination_coords = search_query
        display_name = search_query

    travel_info, encoded_coords = get_drive_time(origin, destination_coords, raw_query)

    if not encoded_coords:
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=travel_info)
        )
        return

    nav_link = f"https://www.google.com/maps/dir/?api=1&destination={quote(search_query)}&travelmode=driving"

    line_bot_api.reply_message(
        event.reply_token,
        [
            TextSendMessage(text=travel_info),
            TextSendMessage(text=f"👇 點我開始導航\n{nav_link}")
        ]
    )

if __name__ == "__main__":
    app.run()
