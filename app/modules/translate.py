import json
import os
import re
import time

import google.generativeai as genai
import pandas as pd
import polib
from tqdm import tqdm

from .config import create_safety_settings

SAFETY_SETTINGS = create_safety_settings("BLOCK_NONE")

# 言語名の読み込み（日本語を除外）
with open(
    os.path.join(os.path.dirname(__file__), "..", "json", "languages.json"),
    "r",
    encoding="utf-8",
) as f:
    all_languages = json.load(f)
    LANG_NAMES = {k: v for k, v in all_languages.items() if k != "ja"}

BASE_DIR = os.path.abspath("app")
LOCALE_DIR = os.path.join(BASE_DIR, "translations")
POT_FILE = os.path.join(BASE_DIR, "messages.pot")
CONFIG_FILE = os.path.join(BASE_DIR, "babel.cfg")
LANGUAGES = list(LANG_NAMES.keys())
API_KEY = os.environ.get("GEMINI_API_KEY")
prompt = """Translate the following text to {lang}.
Important instructions:
1. Return ONLY the translated text
2. Do NOT add any placeholders or variables that weren't in the original text
3. Do NOT translate any text that looks like {{variable_name}} - keep it exactly as is
4. Do NOT add any explanatory text or notes

Text to translate: {source_text}"""

# 設定
if not API_KEY:
    raise ValueError("Please set the GEMINI_API_KEY environment variable")
genai.configure(api_key=API_KEY)

model = genai.GenerativeModel(
    model_name="gemini-2.0-flash-lite",
    safety_settings=SAFETY_SETTINGS,
)


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

    # placeholderという文字列がある場合、高確率で誤りなのでやり直しさせる
    validation = set(re.findall(pattern, text)) or "placeholder" in text.lower()
    return validation


def gemini_translate(text: str, target_lang: str):
    """
    Google翻訳を使って国名を翻訳します。

    Args:
        country_name (str): 翻訳する国名（英語を想定）

    Returns:
        str: 翻訳された国名
    """

    while True:
        time.sleep(1.6)  # レートリミット対策

        # geminiに翻訳を依頼
        chat = model.start_chat()
        response = chat.send_message(prompt.format(lang=target_lang, source_text=text))
        translation = response.text.replace("\n", "")

        # プレースホルダーの検証
        result = validate_placeholders(text, translation)
        if not result:
            print(
                f"プレースホルダーが一致しません。元の文字列: {text}、翻訳後の文字列: {translation}",
                flush=True,
            )
        else:
            # プレースホルダーが一致する場合は翻訳を保存
            break
    return translation


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

    # テンプレートファイルの再生成
    os.system(f"cd {BASE_DIR} && pybabel extract -F {CONFIG_FILE} -o {POT_FILE} .")

    # 翻訳ファイルのマージ
    os.system(f"cd {BASE_DIR} && pybabel update -i {POT_FILE} -d {LOCALE_DIR}")

    for lang in LANGUAGES:
        po_file_path = os.path.join(LOCALE_DIR, lang, "LC_MESSAGES", "messages.po")

        # ファイルが存在しない場合は新規作成
        if not os.path.exists(po_file_path):
            os.system(
                f"cd {BASE_DIR} && pybabel init -i {POT_FILE} -d {LOCALE_DIR} -l {lang}"
            )

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
            # 翻訳先言語を取得
            target_lang = LANG_NAMES.get(lang, lang)

            # 翻訳を依頼
            translation = gemini_translate(
                text=entry.msgid,
                target_lang=target_lang,
            )

            # 翻訳結果を保存
            entry.msgstr = translation

            # fuzzy フラグを削除
            if "fuzzy" in entry.flags:
                entry.flags.remove("fuzzy")

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


def add_country_translation():
    """
    database/country.csv に、LANGUAGES で指定された言語コードごとの国名翻訳列を追加します。

    - 既に該当言語の列が存在する場合は何もせずスキップします。
    - 存在しない場合は Google翻訳（英語→各言語）を用いて翻訳し、新しい列として追加します。
    - 翻訳元は "en" 列の国名です。
    """
    # csvファイルを読み込む
    country_csv = os.path.join(BASE_DIR, "database", "countries.csv")

    # dataframeを作成
    country_df = pd.read_csv(country_csv, encoding="utf-8")

    # headersを取得
    header_list = country_df.columns.tolist()

    for language in LANGUAGES:
        # ヘッダーが存在しない場合は追加
        if language not in header_list:
            country_df[language] = ""

            for index, row in tqdm(
                country_df.iterrows(),
                total=country_df.shape[0],
                desc=f"{language} の国名翻訳",
            ):
                # 英語名はすべてあるので、それを翻訳する
                en_country_name = row["en"]

                # 国名が "-" の場合はスキップ
                if en_country_name == "-":
                    country_df.at[index, language] = "-"
                    continue

                # Google翻訳を使って国名を翻訳
                country_df.at[index, language] = gemini_translate(
                    text=en_country_name,
                    target_lang=language,
                )

            # 新しい列を追加したデータフレームを保存
            country_df.to_csv(country_csv, index=False, encoding="utf-8")


if __name__ == "__main__":
    translate()
    add_country_translation()
