import json
import os
import random
from datetime import datetime

import gspread
import Levenshtein
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

    # 環境変数でローカル環境かどうかを判定
    github_token = os.getenv("GITHUB_TOKEN")

    if github_token is not None:
        year_str = str(year)
        dt_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        client = get_client()

        # スプレッドシートを開く
        sheet = client.open("gbbinfo-jpn").sheet1

        # 質問と年を記録
        sheet.insert_row([dt_now, year_str, question, answer], 2)

    else:
        print(year, question, answer, flush=True)


def get_example_questions():
    client = get_client()

    # スプレッドシートを開く
    sheet = client.open("gbbinfo-jpn").sheet1

    # 質問とステータスを取得
    status = sheet.col_values(5)[1:]  # 最初の要素をスキップ
    questions = sheet.col_values(3)[1:]  # 最初の要素をスキップ

    # ステータスが〇の質問だけを抽出
    filtered_questions = [q.upper() for q, s in zip(questions, status) if s == "〇"]

    # ランダムに3つ選定
    threshold = 0.2
    while True:
        selected_questions = random.sample(filtered_questions, 4)
        # 類似度を計算
        similarities = [
            Levenshtein.ratio(selected_questions[i], selected_questions[j])
            for i in range(len(selected_questions))
            for j in range(i + 1, len(selected_questions))
        ]
        # 類似度が閾値未満であれば終了
        if max(similarities) <= threshold:
            break

    return selected_questions
