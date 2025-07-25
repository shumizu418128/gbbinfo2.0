import asyncio
import json
import os
import random
import re
from threading import Thread

import pandas as pd
import pykakasi
from asyncio_throttle import Throttler
from cachetools import TTLCache
from google import genai
from rapidfuzz import process

from . import spreadsheet
from .config import AVAILABLE_YEARS, create_safety_settings
from .core.utils import find_others_url
from .prompts import get_prompt

API_KEY = os.environ.get("GEMINI_API_KEY")
if not API_KEY:
    raise ValueError("Please set the GEMINI_API_KEY environment variable")
client = genai.Client(api_key=API_KEY)

SAFETY_SETTINGS = create_safety_settings("BLOCK_ONLY_HIGH")

HIRAGANA = "H"
KATAKANA = "K"
KANJI = "J"
ALPHABET = "a"

limiter = Throttler(rate_limit=1, period=2)

# othersファイルを読み込む
if "others_link" not in locals():
    others_templates_path = os.path.join(os.getcwd(), "app", "templates", "others")
    others_link = os.listdir(others_templates_path)

kakasi = pykakasi.kakasi()
kakasi.setMode(HIRAGANA, ALPHABET)  # ひらがなをローマ字に変換
kakasi.setMode(KATAKANA, ALPHABET)  # カタカナをローマ字に変換
kakasi.setMode(KANJI, ALPHABET)  # 漢字をローマ字に変換
converter = kakasi.getConverter()

# URLのキャッシュを辞書として読み込む
cache_file_path = os.path.join(os.getcwd(), "app", "json", "cache.json")
with open(cache_file_path, "r", encoding="utf-8") as f:
    cache = json.load(f)

# cacheのkeyをすべて大文字に変換しておく
cache = {key.upper(): value for key, value in cache.items()}

# 同じ質問が2回来ることがあるので、簡易キャッシュを保存
last_question_cache = TTLCache(maxsize=100, ttl=60)

# 最新年度と1年前の出場者一覧を読み込む
years_to_consider = sorted(AVAILABLE_YEARS, reverse=True)[:2]

# 出場者名リストを作成
name_list = []
for year in years_to_consider:
    participants_csv_path = os.path.join(
        os.getcwd(), "app", "database", "participants", f"{year}.csv"
    )
    beatboxers_df = pd.read_csv(participants_csv_path)
    beatboxers_df = beatboxers_df.fillna("")

    # まずは個人出場者・チーム名のリストを読み込む
    names = (
        beatboxers_df["name"]
        .str.replace("[cancelled] ", "", regex=False)
        .str.upper()
        .tolist()
    )
    name_list.extend(names)

    # 複数名部門メンバーのリストを読み込む
    team_members_list = beatboxers_df["members"].astype(str).str.upper().tolist()
    for team_members in team_members_list:
        if team_members != "":
            member = team_members.split(", ")
            name_list.extend(member)

name_list = list(set(name_list))

# 出場者名をキャッシュに追加
for name in name_list:
    if not name.startswith("?"):
        cache[name] = f"/__year__/participants?scroll=search_participants&value={name}"

# キャッシュのキーをリストに変換
cache_text = [key for key in cache.keys()]


# MARK: キャッシュ検索
def search_cache(year: int, question: str):
    """
    キャッシュの中にユーザーの入力があるか確認し、ある場合は回答を確定します。

    Args:
        year (int): 質問が関連する年。
        question (str): ユーザーからの質問。
    Returns:
        dict: キャッシュにユーザーの入力がある場合、回答を含む辞書。ない場合はNone。
    """
    global last_question_cache

    # 前処理
    question_edited = question.strip().upper()

    # キャッシュにユーザーの入力があるか確認
    if question_edited in cache:
        print("Cache hit", flush=True)

        # キャッシュにユーザーの入力がある場合、回答を確定
        response_url = cache[question_edited].replace("__year__", str(year))

        # スプシに記録
        Thread(
            target=spreadsheet.record_question,
            args=(year, question, response_url),
        ).start()

        return {"url": response_url}

    # 前回の質問と同じ場合はキャッシュを返す
    if question in last_question_cache:
        print("Cache hit", flush=True)
        return last_question_cache[question]

    return None


# MARK: URL作成
def create_url(year: int, url: str, parameter: str | None, name: str | None):
    """
    指定された情報に基づいてレスポンスURLを作成します。

    Args:
        year (int): 質問が関連する年。
        url (str): ベースURL。
        parameter (str): スクロール位置を示すパラメータ。
        name (str): 質問に含まれている名前。

    Returns:
        str: 作成されたURL。
    """

    # topのNoneは問い合わせに変更
    if "top" in url and parameter is None:
        parameter = "contact"

    # 7toSmoke最新情報の場合は7tosmokeこれだけガイドページに変更
    if url == "/others/7tosmoke" and parameter in ["latest_info", None]:
        url = f"/{year}/top_7tosmoke"

    # レスポンスURLの作成
    response_url = url

    # パラメータがある場合は追加
    if bool(parameter) and parameter != "search_participants":
        response_url += f"?scroll={parameter}"

    # participantsのsearch_participantsが指定された場合はvalueに質問を追加
    if parameter == "search_participants" and bool(name):
        # search_participantsのとき、nameがある場合のみ追加
        response_url += "?scroll=search_participants"

        # 英数字表記かどうか判定
        # 記号も対象・Ωは"Sound of Sony Ω"の入力対策
        alphabet_pattern = r'^[a-zA-Z0-9 \-!@#$%^&*()_+=~`<>?,.\/;:\'"\\|{}[\]Ω]+'
        match_alphabet = re.match(alphabet_pattern, name)

        # 英数字表記の場合、大文字に変換して追加
        if match_alphabet:
            response_url += f"&value={match_alphabet.group().upper()}"

        # それ以外の場合、ローマ字に変換して追加
        else:
            romaji_name = converter.do(name)

            # 一応ちゃんと変換できたか確認
            match_alphabet = re.match(alphabet_pattern, romaji_name)
            if match_alphabet:
                response_url += f"&value={romaji_name.upper()}"
            else:
                response_url += f"&value={name}"

    return response_url


# MARK: gemini ページ内検索
def search(year: int, question: str):
    """
    指定された年と質問に基づいてチャットを開始し、モデルからの応答を取得します。

    Args:
        year (int): 質問が関連する年。
        question (str): ユーザーからの質問。

    Returns:
        dict: モデルからの応答を含む辞書。URLが含まれます。
    """
    global others_link, last_question_cache

    # 年度を推定：数字を検出
    detect_year = re.search(r"\d{4}", question)
    detect_year_2 = re.search(r"\d{2}", question)

    # 数字が検出された場合、そこから年度を推定
    if detect_year or detect_year_2:
        if detect_year:
            detect_year = int(detect_year.group())
        else:
            detect_year = int(detect_year_2.group())
            detect_year += 2000

        # 2022年度の場合はトップページへリダイレクト
        if detect_year == 2022:
            return {"url": "/2022/top"}

        # 2022年度以外の場合は年度を更新
        if detect_year in AVAILABLE_YEARS and detect_year != year:
            year = detect_year

    # ask_gemini関数を使用してAPIを呼び出し
    # 最も安全なイベントループ処理
    try:
        response_dict = asyncio.run(ask_gemini(year, question))
    except RuntimeError:
        return None
    except Exception as e:
        print(f"イベントループエラー: {e}", flush=True)
        return None

    # othersのリンクであればリンクを変更
    others_url = find_others_url(response_dict["url"], others_link)
    if others_url:
        response_dict["url"] = others_url

    # URLとパラメータの正規化処理
    url = response_dict["url"].split("%")[0]
    parameter = (
        None if response_dict["parameter"] == "None" else response_dict["parameter"]
    )
    name = None if response_dict["name"] == "None" else response_dict["name"]

    # レスポンスURLの作成
    response_url = create_url(year, url, parameter, name)

    print(year, question, response_url, flush=True)

    # スプシに記録
    Thread(
        target=spreadsheet.record_question, args=(year, question, response_url)
    ).start()

    # キャッシュに保存
    try:
        last_question_cache[question] = {"url": response_url}
    except Exception:
        pass

    return {"url": response_url}


# MARK: gemini API呼び出し関数
async def ask_gemini(year: int, question: str):
    """
    Gemini APIに質問を送信する関数。
    グローバルなレート制限で2秒間隔を保証し、最大5回リトライします。

    Args:
        year (int): 質問が関連する年。
        question (str): ユーザーからの質問。

    Returns:
        dict: Gemini APIからのレスポンスを辞書形式で返す

    Raises:
        Exception: 5回リトライしても失敗した場合に発生
    """

    # 最大5回リトライ
    async with limiter:
        for attempt in range(5):
            try:
                # チャットを開始
                chat = client.chats.create(
                    model="gemini-2.0-flash-lite",
                    config={
                        "response_mime_type": "application/json",
                        "safety_settings": SAFETY_SETTINGS,
                    },
                )

                # プロンプトに必要事項を埋め込む
                prompt_formatted = get_prompt(year, question)
                print(f"question: {question}", flush=True)

                # メッセージを送信
                response = chat.send_message(prompt_formatted)

                # レスポンスをダブルクォーテーションに置き換え
                response_text = response.text.replace("'", '"')

                # レスポンスをJSONに変換
                response_dict = json.loads(
                    response_text.replace("https://gbbinfo-jpn.onrender.com", "")
                )

                # リスト形式の場合は最初の要素を取得
                if isinstance(response_dict, list) and len(response_dict) > 0:
                    response_dict = response_dict[0]

                return response_dict

            except Exception as e:
                print(f"Gemini API呼び出し失敗 (試行 {attempt + 1}/5): {e}", flush=True)
                if attempt == 4:  # 最後の試行
                    raise e
                await asyncio.sleep(2)


# MARK: サイト内検索候補
def search_suggestions(input: str):
    """
    ユーザーの入力に基づいて、サイト内の検索候補を生成します。

    Args:
        input (str): ユーザーからの入力。

    Returns:
        list: 類似する出場者名のリスト。
    """
    # 下処理：inputから4桁・2桁の年削除
    year = re.search(r"\d{4}", input)
    year_2 = re.search(r"\d{2}", input)
    if year:
        year = year.group()
        input = input.replace(year, "")
    if year_2:
        year_2 = year_2.group()
        input = input.replace(year_2, "")

    # 下処理：inputから空白削除
    input = input.strip().upper().replace("GBB", "")

    # rapidfuzzで類似度を計算し、上位3件を取得
    random.shuffle(cache_text)
    suggestions = process.extract(input, cache_text, limit=3, score_cutoff=1)

    # rapidfuzzの結果から検索候補を取得
    suggestions = [result[0] for result in suggestions]

    # 結果を返す
    return suggestions
