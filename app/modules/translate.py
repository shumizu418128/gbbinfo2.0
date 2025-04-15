import json
import os
import re
import sys
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

BASE_DIR = os.path.abspath("app")
LOCALE_DIR = os.path.join(BASE_DIR, "translations")
POT_FILE = os.path.join(BASE_DIR, "messages.pot")
CONFIG_FILE = os.path.join(BASE_DIR, "babel.cfg")
LANGUAGES = [
    d for d in os.listdir(LOCALE_DIR) if os.path.isdir(os.path.join(LOCALE_DIR, d))
]
API_KEY = os.environ.get("GEMINI_API_KEY")

prompt = """
# Input
Text: {source_text}
Language: {lang}

# Output
{{"translated_text": "(ここに翻訳文)"}}

# Note
- Ensure proper JSON escaping for quotes, backslashes, and control characters.
- Placeholders enclosed in {{}} (e.g., {{year}}) are variable names and should not be translated.
"""


def extract_placeholders(text):
    """
    文字列からプレースホルダー `{name}` を抽出します。

    プレースホルダーは、特定の値を動的に挿入するために使用されるテキスト内のマーカーです。
    この関数は、与えられたテキスト内のすべてのプレースホルダーを検出し、それらをセットとして返します。

    例:
    - 入力: "こんにちは、{name}さん！"
    - 出力: {'name'}

    Args:
        text (str): プレースホルダーを抽出する対象の文字列。

    Returns:
        set: 文字列から抽出されたプレースホルダー名のセット。
             プレースホルダーが見つからない場合は、空のセットを返します。
    """
    pattern = r"\{([^}]+)\}"
    return set(re.findall(pattern, text))


def validate_placeholders(msgid, msgstr):
    """
    msgid (元の文字列) と msgstr (翻訳後の文字列) に含まれるプレースホルダーを比較し、
    両者のプレースホルダーが一致するかどうかを検証します。

    プレースホルダーとは、`{変数名}` の形式で文字列内に埋め込まれた動的な値の挿入箇所を示すものです。
    この関数は、翻訳の品質を保証するために、元の文字列と翻訳後の文字列でプレースホルダーが
    正確に対応しているかを確認します。

    Args:
        msgid (str): 元の文字列 (翻訳元)。
        msgstr (str): 翻訳後の文字列。

    Returns:
        bool: プレースホルダーが一致する場合は True、一致しない場合は False を返します。
               プレースホルダーが一致しない場合は、警告メッセージを標準出力に出力します。
    """
    src_placeholders = extract_placeholders(msgid)
    trans_placeholders = extract_placeholders(msgstr)

    if src_placeholders != trans_placeholders:
        return False
    return True


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
    if not API_KEY:
        raise ValueError("Please set the GEMINI_API_KEY environment variable")
    genai.configure(api_key=API_KEY)

    model = genai.GenerativeModel(
        model_name="gemini-2.0-flash-lite-preview",
        safety_settings=SAFETY_SETTINGS,
        generation_config={"response_mime_type": "application/json"},
    )

    # テンプレートファイルの再生成
    os.system(f"cd {BASE_DIR} && pybabel extract -F {CONFIG_FILE} -o {POT_FILE} .")

    # 翻訳ファイルのマージ
    os.system(f"cd {BASE_DIR} && pybabel update -i {POT_FILE} -d {LOCALE_DIR}")

    for lang in LANGUAGES:
        po_file_path = os.path.join(LOCALE_DIR, lang, "LC_MESSAGES", "messages.po")
        po = polib.pofile(po_file_path)

        # 既存の翻訳のプレースホルダーを検証
        print(f"\n{lang}の翻訳を検証中...")
        for entry in po:
            if entry.msgstr:  # 翻訳が存在する場合のみチェック
                result = validate_placeholders(entry.msgid, entry.msgstr)

                # プレースホルダーが一致しない場合は fuzzy フラグを追加
                if not result:
                    entry.flags.append("fuzzy")

        po.save(po_file_path)  # プレースホルダーの検証結果を保存
        po = polib.pofile(po_file_path)  # 再度ファイルを読み込む

        for entry in tqdm(
            po.untranslated_entries() + po.fuzzy_entries(), desc=f"{lang} の翻訳"
        ):
            # geminiチャットを開始
            while True:
                time.sleep(1.5)
                try:
                    # geminiに翻訳を依頼
                    chat = model.start_chat()
                    response = chat.send_message(
                        prompt.format(lang=lang, source_text=entry.msgid)
                    )
                    response_json = json.loads(response.text)

                    # レスポンスの形式を確認
                    if isinstance(response_json, list):
                        response_json = response_json[0]
                    translation = list(response_json.values())[0]
                    translation = translation.replace("\\", "")

                    # プレースホルダーの検証
                    result = validate_placeholders(entry.msgid, translation)

                    # プレースホルダーが一致する場合は翻訳を保存
                    # 明らかに不正な翻訳はスキップ
                    if result and translation not in "ここに翻訳文":
                        entry.msgstr = translation

                        # fuzzy フラグを削除
                        if "fuzzy" in entry.flags:
                            entry.flags.remove("fuzzy")
                        break

                except Exception as e:
                    _, _, exc_tb = sys.exc_info()
                    line_number = exc_tb.tb_lineno
                    print(
                        f"{e.__class__.__name__}: {e} (行番号: {line_number})\n再試行中...",
                        flush=True,
                    )

        po.save(po_file_path)

    # 再コンパイル
    os.system(f"cd {BASE_DIR} && pybabel compile -d {LOCALE_DIR}")

    # 不要な翻訳を削除
    for lang in LANGUAGES:
        # ファイルを読み込む
        po_file_path = os.path.join(LOCALE_DIR, lang, "LC_MESSAGES", "messages.po")
        with open(po_file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        with open(po_file_path, "w", encoding="utf-8") as f:
            for line in lines:
                if not line.startswith("#~ "):
                    f.write(line)
        print(f"{lang} の不要な翻訳を削除しました。", flush=True)

    print("翻訳が完了しました！", flush=True)


if __name__ == "__main__":
    translate()
