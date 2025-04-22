from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import requests
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

line_bot_api = LineBotApi(os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))
handler = WebhookHandler(os.getenv("LINE_CHANNEL_SECRET"))
GOOGLE_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")

def get_drive_time(destination):
    origin = "台中市西屯區逢明街29巷70號"  # ⬅️ 你可自行修改固定起點
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
        return f"{destination}\n1651黑 🈲代駕\n查詢失敗：找不到路線"

    try:
        leg = response['routes'][0]['legs'][0]
        duration_text = leg.get('duration_in_traffic', {}).get('text')
        if not duration_text:
            duration_text = leg['duration']['text']

        # 取分鐘數 + 2 分鐘（保險時間）
        minutes = int(''.join(filter(str.isdigit, duration_text))) + 2

        return f"{destination}\n1651黑 🈲代駕\n{minutes}分"
    except Exception as e:
        return f"{destination}\n1651黑 🈲代駕\n查詢失敗：{str(e)}"

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
def handle_message(event):
    user_text = event.message.text
    reply = get_drive_time(user_text)
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply)
    )

if __name__ == "__main__":
    app.run()
