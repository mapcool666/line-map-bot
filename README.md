
# Line Map Bot

一個使用 Google Maps API 回覆開車時間的 LINE Bot。

## 使用方式

1. 填寫 `.env` 檔案（依照 `.env.example` 格式）
2. 執行 `pip install -r requirements.txt`
3. 執行 `python app.py`
4. 用 ngrok 開通：`ngrok http 5000`
5. 將 ngrok 網址貼到 LINE Webhook URL
