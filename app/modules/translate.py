import json
import os
import time

import google.generativeai as genai
import polib
from tqdm import tqdm

SAFETY_SETTINGS = [
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
    },
]

prompt = """
# Task
Translate the following text into {lang}.

# Input
Text: {source_text}
Target Language: {lang}

# Output Format (JSON)
{{"translated_text": "string"}}

# Note
The output will be parsed using Python's `json.loads` function.
Please ensure that any characters requiring escaping for `json.loads` to correctly parse the JSON are properly escaped.
This includes, but is not limited to, double quotes, backslashes, and control characters.
"""


def translate():
    """
    翻訳プロセスを自動化する関数。

    この関数は以下のステップを実行します:
    1. テンプレートファイル (.pot) を再生成します。
    2. 既存の翻訳ファイル (.po) をテンプレートファイルとマージします。
    3. 未翻訳のエントリを Google Translate で翻訳します。
    4. 翻訳された内容で翻訳ファイルを更新します。
    5. 翻訳ファイルをコンパイルして、実行時に使用できる形式にします。

    ローカルでの実行を前提としています。
    """
    # 設定
    API_KEY = os.environ.get("GEMINI_API_KEY")
    if not API_KEY:
        raise ValueError("Please set the GEMINI_API_KEY environment variable")
    genai.configure(api_key=API_KEY)

    model = genai.GenerativeModel(
        model_name="gemini-2.0-flash-lite-preview",
        safety_settings=SAFETY_SETTINGS,
        generation_config={"response_mime_type": "application/json"},
    )

    BASE_DIR = os.path.abspath("app")
    LOCALE_DIR = os.path.join(BASE_DIR, "translations")
    POT_FILE = os.path.join(BASE_DIR, "messages.pot")
    CONFIG_FILE = os.path.join(BASE_DIR, "babel.cfg")
    LANGUAGES = [
        d for d in os.listdir(LOCALE_DIR) if os.path.isdir(os.path.join(LOCALE_DIR, d))
    ]

    # テンプレートファイルの再生成
    os.system(f"cd {BASE_DIR} && pybabel extract -F {CONFIG_FILE} -o {POT_FILE} .")

    # 翻訳ファイルのマージ
    os.system(f"cd {BASE_DIR} && pybabel update -i {POT_FILE} -d {LOCALE_DIR}")

    # geminiで翻訳
    for lang in LANGUAGES:
        po_file_path = os.path.join(LOCALE_DIR, lang, "LC_MESSAGES", "messages.po")
        po = polib.pofile(po_file_path)

        for entry in tqdm(
            po.untranslated_entries() + po.fuzzy_entries(), desc=f"{lang} の翻訳", leave=False
        ):
            # geminiチャットを開始
            while True:
                time.sleep(2)
                try:
                    chat = model.start_chat()
                    response = chat.send_message(
                        prompt.format(lang=lang, source_text=entry.msgid)
                    )
                    response_json = json.loads(response.text)
                    break
                except Exception as e:
                    print(response.text)
                    print(f"翻訳エラー：{e}\n再試行中...", flush=True)

            # 翻訳を保存
            if isinstance(response_json, list):
                response_json = response_json[0]
            translation = list(response_json.values())[0]
            translation = translation.replace("\\", "")

            entry.msgstr = translation

            if "fuzzy" in entry.flags:
                entry.flags.remove("fuzzy")  # fuzzy フラグを削除

        po.save(po_file_path)
        print(f"{lang} の翻訳を保存しました。", flush=True)

    # 再コンパイル
    os.system(f"cd {BASE_DIR} && pybabel compile -d {LOCALE_DIR}")

    print("翻訳が完了しました！", flush=True)


if __name__ == "__main__":
    translate()
