import json
import time
import os

import google.generativeai as genai


api_key = os.environ.get("GEMINI_API_KEY")
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


def search(year: int, question: str):
    # チャットを開始
    chat = model.start_chat()

    # 回答例 geminiに教える
    url_example = f"{{\'url\': 'https://gbbinfo-jpn.onrender.com/{year}/top'}}"

    # プロンプトを読み込む
    file_path = os.getcwd() + '/app/gbb_pages.txt'
    with open(file_path, 'r', encoding="utf-8") as f:
        prompt = f.read()

    # プロンプトを埋め込む
    prompt = prompt.format(year=year, question=question, url_example=url_example)
    print(question, flush=True)

    while True:
        try:
            # メッセージを送信
            response = chat.send_message(prompt)
        except Exception as e:
            print(e)
            time.sleep(1)
        else:
            break

    # レスポンスをJSONに変換
    try:
        response_dict = json.loads(response.text.replace('https://gbbinfo-jpn.onrender.com', ''))
    except Exception:
        print("Error: response is not JSON", flush=True)
        response_dict = {'url': f'/{year}/top'}

    # othersディレクトリのリンクがある場合は変換
    for others_link in ["about", "how_to_plan", "result_stream"]:
        if response_dict["url"] == f"/{year}/{others_link}":
            response_dict["url"] = f"/others/{others_link}"
            break

    return response_dict
