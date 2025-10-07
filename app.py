from flask import Flask, render_template, request, jsonify
import pandas as pd
import requests
import base64
from datetime import datetime
from pathlib import Path

app = Flask(__name__)

# 🔐 Spotify API 金鑰（請替換成你自己的）
client_id = "878d5c21e6354bf29674089cca6b5bc9"
client_secret = "817ebebc33c545bcaeb097365a3e50cc"

# 🕒 表單開放時間設定
start_time = datetime(2025, 10, 7, 10, 0)  # 開始時間
end_time = datetime(2025, 10, 7, 22, 0)    # 結束時間

# 📦 暫存使用者點歌資料
pending_requests = []

# 📁 匯出資料夾（可自訂）
export_dir = Path(__file__).resolve().parent

# 🔍 判斷表單是否開放
def is_form_open():
    now = datetime.now()
    return start_time <= now <= end_time

# 🔐 取得 Spotify access token
def get_spotify_token():
    auth_str = f"{client_id}:{client_secret}"
    b64_auth = base64.b64encode(auth_str.encode()).decode()
    res = requests.post("https://accounts.spotify.com/api/token",
        headers={"Authorization": f"Basic {b64_auth}"},
        data={"grant_type": "client_credentials"}
    )
    return res.json()["access_token"]

# 🔍 Spotify 搜尋 API
@app.route("/spotify")
def spotify_search():
    q = request.args.get("q")
    token = get_spotify_token()
    res = requests.get("https://api.spotify.com/v1/search",
        headers={"Authorization": f"Bearer {token}"},
        params={"q": q, "type": "track", "limit": 5}
    )
    data = res.json()
    tracks = []
    for item in data["tracks"]["items"]:
        tracks.append({
            "name": item["name"],
            "artist": item["artists"][0]["name"],
            "url": item["external_urls"]["spotify"]
        })
    return jsonify({"tracks": tracks})

# 🏠 首頁：顯示表單或關閉提示
@app.route("/")
def index():
    return render_template("index.html", form_open=is_form_open())

# 📥 使用者送出點歌資料
@app.route("/submit", methods=["POST"])
def submit():
    if not is_form_open():
        return jsonify({"status": "表單已關閉"})

    data = request.json
    pending_requests.append([
        data["name"],
        data["gender"],
        data["title"],
        data["spotify_url"]
    ])
    return jsonify({"status": "success"})

# 📤 管理者匯出資料為 Excel（含時間戳記）
@app.route("/export", methods=["POST"])
def export_data():
    if not pending_requests:
        return jsonify({"status": "沒有資料可匯出"})

    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    filename = export_dir / f"song_requests_{timestamp}.xlsx"
    df = pd.DataFrame(pending_requests, columns=["requester", "gender", "title", "spotify_url"])
    df.to_excel(filename, index=False)
    pending_requests.clear()
    return jsonify({"status": "匯出完成", "filename": str(filename)})
# 🔐 管理者後台：顯示所有暫存資料
@app.route("/admin")
def admin():
    return render_template("admin.html", data=pending_requests)

import os

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))  # Render 提供的埠號
    print(f"✅ Flask 伺服器啟動中…（port: {port}）")
    app.run(host="0.0.0.0", port=port, debug=True)
