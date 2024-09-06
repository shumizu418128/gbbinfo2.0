import json
import os
from datetime import datetime

import gspread
from google.oauth2.service_account import Credentials
from oauth2client.service_account import ServiceAccountCredentials

credentials = None
client = None


# Googleスプレッドシートに接続
def get_client():
    global credentials, client
    if credentials is None:

        # スコープと認証
        scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive"
        ]
        # 認証情報を環境変数から取得
        path = os.environ.get("GOOGLE_SHEET_CREDENTIALS")

        if path is None:
            # 認証情報を取得
            credentials = ServiceAccountCredentials.from_json_keyfile_name(
                "D://おもちゃ/makesomenoise-4cb78ac4f8b5.json", scope
            )
        else:
            # 環境変数から認証情報を取得
            credentials_info = json.loads(path)

            # 認証情報を作成
            credentials = Credentials.from_service_account_info(
                credentials_info, scopes=scope)

    if client is None:
        client = gspread.authorize(credentials)

    return client


# Googleスプレッドシートに記録
def record_question(year: int, question: str, answer: str):
    year_str = str(year)
    dt_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    client = get_client()

    # スプレッドシートを開く
    sheet = client.open("gbbinfo-jpn").sheet1

    # 質問と年を記録
    sheet.append_row([dt_now, year_str, question, answer])
