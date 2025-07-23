import json
import os
from datetime import datetime

import gspread
import ratelimit
from google.oauth2.service_account import Credentials

# 環境変数でローカル環境かどうかを判定
ENVIRONMENT_CHECK = os.getenv("ENVIRONMENT_CHECK")

# スコープと認証
SCOPE = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]

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
        # 認証情報を環境変数から取得
        path = os.environ.get("GOOGLE_SHEET_CREDENTIALS")

        # 環境変数から認証情報を取得
        credentials_info = json.loads(path)

        # 認証情報を作成
        credentials = Credentials.from_service_account_info(
            credentials_info, scopes=SCOPE
        )

    if client is None:
        client = gspread.authorize(credentials)

    return client


# Googleスプレッドシートに記録
# 3秒間に1回のリクエストを許可
@ratelimit.limits(calls=1, period=3, raise_on_limit=False)
def record_question(year: int, question: str, answer: str):
    """
    Googleスプレッドシートに質問と回答を記録します。
    環境変数を使用してローカル環境かどうかを判定し、スプレッドシートにデータを挿入します。

    Args:
        year (int): 質問が関連する年。
        question (str): 記録する質問。
        answer (str): 記録する回答。
    Returns:
        None: (結果を記録)
    """

    # ローカル環境・プルリクエストの場合は記録しない
    if (
        ENVIRONMENT_CHECK == "qawsedrftgyhujikolp"
        or os.getenv("IS_PULL_REQUEST") == "true"
    ):
        return

    year_str = str(year)
    dt_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    client = get_client()

    # スプレッドシートを開く
    sheet = client.open("gbbinfo-jpn").worksheet("questions")

    # 質問と年を記録
    sheet.insert_row([dt_now, year_str, question, answer], 2)
