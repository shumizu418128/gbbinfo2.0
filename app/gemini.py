import json
import os
import re
import time
from threading import Thread

import google.generativeai as genai

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
    file_path = os.getcwd() + '/app/gbb_pages.txt'
    with open(file_path, 'r', encoding="utf-8") as f:
        prompt = f.read()

# othersファイルを読み込む
if 'others_link' not in locals():
    others_link = os.listdir(os.getcwd() + '/app/templates/others')


def search(year: int, question: str):
    """
    指定された年と質問に基づいてチャットを開始し、モデルからの応答を取得します。

    Args:
        year (int): 質問が関連する年。
        question (str): ユーザーからの質問。

    Returns:
        dict: モデルからの応答を含む辞書。辞書には以下のキーが含まれます。
            - url (str): レスポンスURL。
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
    others_url = next((f"/others/{link.replace('.html', '')}" for link in others_link if link.replace(".html", "") in response_dict["url"]), None)
    if others_url:
        response_dict["url"] = others_url

    # URLとパラメータの正規化処理
    response_dict["url"] = response_dict["url"].split("%")[0]
    response_dict["parameter"] = None if response_dict["parameter"] == "None" else response_dict["parameter"]

    # topのNoneは問い合わせに変更
    if "top" in response_dict["url"] and response_dict["parameter"] is None:
        response_dict["parameter"] = "contact"

    # 7toSmoke最新情報の場合は7tosmokeこれだけガイドページに変更
    if response_dict["url"] == "/others/7tosmoke" and response_dict["parameter"] in ["latest_info", None]:
        response_dict["url"] = f"/{year}/top_7tosmoke"

    # レスポンスURLの作成
    response_url = response_dict["url"]

    # パラメータがある場合は追加
    if bool(response_dict["parameter"]):
        parameter = response_dict["parameter"]
        response_url += f"?scroll={parameter}"

    # participantsのsearch_participantsが指定された場合はvalueに質問を追加
    if response_dict["parameter"] == "search_participants":
        match = re.search(r'^[a-zA-Z0-9 \-!@#$%^&*()_+=~`<>?,.\/;:\'"\\|{}[\]Ω]+', question)
        if match:
            response_url += f"&value={match.group().upper()}"

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
