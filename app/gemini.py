import json
import os
import re
import time
from threading import Thread

import google.generativeai as genai
import pykakasi

from . import spreadsheet

api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    raise ValueError("Please set the GEMINI_API_KEY environment variable")
genai.configure(api_key=api_key)

safety_settings = [
    {
        "category": "HARM_CATEGORY_SEXUAL",
        "threshold": "BLOCK_NONE",
    },
    {
        "category": "HARM_CATEGORY_DANGEROUS",
        "threshold": "BLOCK_NONE",
    },
    {
        "category": "HARM_CATEGORY_HARASSMENT",
        "threshold": "BLOCK_NONE",
    },
    {
        "category": "HARM_CATEGORY_HATE_SPEECH",
        "threshold": "BLOCK_NONE",
    },
    {
        "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
        "threshold": "BLOCK_NONE",
    },
    {
        "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
        "threshold": "BLOCK_NONE",
    }
]

model = genai.GenerativeModel(
    model_name='gemini-1.5-flash-latest',
    safety_settings=safety_settings,
    generation_config={"response_mime_type": "application/json"}
)

# プロンプトを読み込む
if 'prompt' not in locals():
    file_path = os.getcwd() + '/app/prompt.txt'
    with open(file_path, 'r', encoding="utf-8") as f:
        prompt = f.read()

# othersファイルを読み込む
if 'others_link' not in locals():
    others_link = os.listdir(os.getcwd() + '/app/templates/others')

kakasi = pykakasi.kakasi()
kakasi.setMode('H', 'a')  # ひらがなをローマ字に変換
kakasi.setMode('K', 'a')  # カタカナをローマ字に変換
kakasi.setMode('J', 'a')  # 漢字をローマ字に変換
converter = kakasi.getConverter()


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
        match_alphabet = re.match(
            r'^[a-zA-Z0-9 \-!@#$%^&*()_+=~`<>?,.\/;:\'"\\|{}[\]Ω]+',
            name
        )

        # 英数字表記の場合、大文字に変換して追加
        if match_alphabet:
            response_url += f"&value={match_alphabet.group().upper()}"

        # それ以外の場合、ローマ字に変換して追加
        else:
            romaji_name = converter.do(name)

            # 一応ちゃんと変換できたか確認
            match_alphabet = re.match(
                r'^[a-zA-Z0-9 \-!@#$%^&*()_+=~`<>?,.\/;:\'"\\|{}[\]Ω]+',
                romaji_name
            )
            if match_alphabet:
                response_url += f"&value={romaji_name.upper()}"

    return response_url


def search(year: int, question: str):
    """
    指定された年と質問に基づいてチャットを開始し、モデルからの応答を取得します。

    Args:
        year (int): 質問が関連する年。
        question (str): ユーザーからの質問。

    Returns:
        dict: モデルからの応答を含む辞書。辞書には以下のキーが含まれます。
            url (str): レスポンスURL。
    """
    global prompt, others_link

    # チャットを開始
    chat = model.start_chat()

    # プロンプトに必要事項を埋め込む
    prompt_formatted = prompt.format(
        year=year,
        question=question
    )
    print(question, flush=True)

    while True:
        try:
            # メッセージを送信
            response = chat.send_message(prompt_formatted)
        except Exception as e:
            print(e)
            time.sleep(1)
        else:
            break

    # レスポンスをJSONに変換
    try:
        response_dict = json.loads(
            response.text.replace(
                'https://gbbinfo-jpn.onrender.com', ''
            )
        )
    except json.JSONDecodeError:
        print("Error: response is not JSON", flush=True)
        # JSONデコード失敗時のデフォルト値
        return {'url': f'/{year}/top', 'parameter': 'contact'}

    # othersのリンクであればリンクを変更
    others_url = next(
        (
            f"/others/{link.replace('.html', '')}"
            for link in others_link
            if link.replace(".html", "") in response_dict["url"]
        ),
        None
    )
    if others_url:
        response_dict["url"] = others_url

    # URLとパラメータの正規化処理
    url = response_dict["url"].split("%")[0]
    parameter = None if response_dict["parameter"] == "None" else response_dict["parameter"]
    name = None if response_dict["name"] == "None" else response_dict["name"]

    # レスポンスURLの作成
    response_url = create_url(year, url, parameter, name)

    # スプシに記録
    if question != "テスト":
        Thread(
            target=spreadsheet.record_question,
            args=(
                year,
                question,
                response_url
            )
        ).start()

    return {"url": response_url}
