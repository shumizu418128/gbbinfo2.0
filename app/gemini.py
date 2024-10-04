import json
import os
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
    global prompt, others_link

    # チャットを開始
    chat = model.start_chat()

    # 回答例 geminiに教える
    url_example = f"{{\'url\': 'https://gbbinfo-jpn.onrender.com/{year}/top', 'parameter': 'contact'}}"

    # プロンプトを埋め込む
    prompt_formatted = prompt.format(
        year=year,
        question=question,
        url_example=url_example
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
        response_dict = {
            'url': f'/{year}/top',
            'parameter': None
        }  # ここでparameterも初期化

    # othersのリンクであればリンクを変更
    for link in others_link:
        if link.replace(".html", "") in response_dict["url"]:
            response_dict["url"] = f"/others/{link.replace('.html', '')}"
            break

    # リンクに説明が含まれている場合は削除
    if "%" in response_dict["url"]:
        response_dict["url"] = response_dict["url"].split("%")[0]

    ########################################################

    # パラメータの例外処理
    # parameterのNone処理
    if response_dict["parameter"] == "None":
        response_dict["parameter"] = None

    # topのNoneは問い合わせに変更
    if "top" in response_dict["url"] and response_dict["parameter"] is None:
        response_dict["parameter"] = "contact"

    ########################################################

    # レスポンスURLの作成
    response_url = response_dict["url"]

    # パラメータがある場合は追加
    if bool(response_dict["parameter"]):
        parameter = response_dict["parameter"]
        response_url += f"?scroll={parameter}"

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
