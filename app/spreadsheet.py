import json
import os
import random
from datetime import datetime
import ratelimit

import gspread
import Levenshtein
from google.oauth2.service_account import Credentials
from oauth2client.service_account import ServiceAccountCredentials

credentials = None
client = None


# Googleスプレッドシートに接続
def get_client():
    """
    Googleスプレッドシートに接続するためのクライアントを取得します。

    環境変数から認証情報を取得し、gspreadを使用してGoogleスプレッドシートに接続します。
    認証情報が未設定の場合は、デフォルトのJSONファイルから取得します。

    Returns:
        gspread.Client: Googleスプレッドシートに接続するためのクライアントオブジェクト。
    """
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
# 3秒間に1回のリクエストを許可
@ratelimit.limits(calls=1, period=3)
def record_question(year: int, question: str, answer: str):
    """
    Googleスプレッドシートに質問と回答を記録します。
    環境変数を使用してローカル環境かどうかを判定し、スプレッドシートにデータを挿入します。

    Args:
        year (int): 質問が関連する年。
        question (str): 記録する質問。
        answer (str): 記録する回答。
    """
    # 環境変数でローカル環境かどうかを判定
    github_token = os.getenv("GITHUB_TOKEN")

    if github_token is not None:
        year_str = str(year)
        dt_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        client = get_client()

        # スプレッドシートを開く
        sheet = client.open("gbbinfo-jpn").sheet1

        # 直前の質問(C2)を取得、同じ質問があれば終了
        last_question = sheet.acell("C2").value

        if last_question == question:
            print("The same question has already been recorded.", flush=True)
            return

        # 質問と年を記録
        sheet.insert_row([dt_now, year_str, question, answer], 2)

    else:
        print(year, question, answer, flush=True)


def get_example_questions():
    """
    スプレッドシートから例の質問を取得し、ランダムに選定します。

    ステータスが〇の質問のみを抽出し、類似度が閾値未満の質問をランダムに選びます。

    Returns:
        list: 選定された質問のリスト。
    """
    client = get_client()

    # スプレッドシートを開く
    sheet = client.open("gbbinfo-jpn").sheet1

    # 質問とステータスを取得
    status = sheet.col_values(5)[1:]  # 最初の要素をスキップ
    questions = sheet.col_values(3)[1:]  # 最初の要素をスキップ

    # ステータスが〇の質問だけを抽出
    filtered_questions = [q.upper().strip() for q, s in zip(questions, status) if s == "〇"]

    # 重複を削除
    filtered_questions = list(set(filtered_questions))

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
