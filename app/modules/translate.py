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


def is_translated(url, target_lang=None, translated_paths=None):
    """
    POファイルを読み込んで、指定されたページに翻訳が提供されているかをチェックします。

    Args:
        url (str): ページのURL
        target_lang (str): 対象言語（Noneの場合は現在のセッション言語）
        translated_paths (set): 翻訳されたパスのセット（Noneの場合は遅延読み込み）

    Returns:
        bool: 翻訳が提供されている場合True、されていない場合False
    """
    # 日本語の場合は常にTrue（元言語）
    if target_lang == "ja":
        return True

    # 遅延読み込みで翻訳パスを取得
    if translated_paths is None:
        from .optimization.cache import persistent_cache

        translated_paths = persistent_cache.get_translated_paths()

    return url in translated_paths


# 言語名の読み込み（日本語を除外）
with open(
    os.path.join(os.path.dirname(__file__), "..", "json", "languages.json"),
    "r",
    encoding="utf-8",
) as f:
    all_languages = json.load(f)
    LANG_NAMES = {k: v for k, v in all_languages.items() if k != "ja"}

# ローカル翻訳用の設定
BASE_DIR = os.path.abspath("app")
LOCALE_DIR = os.path.join(BASE_DIR, "translations")
POT_FILE = os.path.join(BASE_DIR, "messages.pot")
CONFIG_FILE = os.path.join(BASE_DIR, "babel.cfg")
LANGUAGES = list(LANG_NAMES.keys())

# Gemini API設定（ローカル翻訳用）
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

    Args:
        text (str): プレースホルダーを抽出する対象の文字列。

    Returns:
        set: 文字列から抽出されたプレースホルダー名のセット。
    """
    pattern = r"\{([^}]+)\}"
    validation = set(re.findall(pattern, text)) or "placeholder" in text.lower()
    return validation


def validate_placeholders(msgid, msgstr):
    """
    プレースホルダーの検証を行います。

    Args:
        msgid (str): 元の文字列 (翻訳元)。
        msgstr (str): 翻訳後の文字列。

    Returns:
        bool: プレースホルダーが一致する場合は True、一致しない場合は False。
    """
    src_placeholders = extract_placeholders(msgid)
    trans_placeholders = extract_placeholders(msgstr)

    if src_placeholders != trans_placeholders:
        return False
    return True


def gemini_translate(text: str, target_lang: str):
    """
    Google Gemini AIを使用してテキストを指定された言語に翻訳します。

    Args:
        text (str): 翻訳するテキスト。
        target_lang (str): 翻訳先の言語名。

    Returns:
        str: 翻訳されたテキスト。
    """
    if not model:
        raise ValueError("Gemini API key not configured")

    while True:
        # シンプルなレートリミット（2秒間隔）
        time.sleep(2)

        try:
            # geminiに翻訳を依頼
            chat = model.start_chat()
            response = chat.send_message(
                prompt.format(lang=target_lang, source_text=text)
            )
            translation = response.text.replace("\n", "")

            # プレースホルダーの検証
            result = validate_placeholders(text, translation)
            if not result:
                print(
                    f"プレースホルダーが一致しません。再翻訳します。元の文字列: {text}、翻訳後の文字列: {translation}",
                    flush=True,
                )
                continue
            else:
                break
        except Exception as e:
            print(
                f"Gemini API呼び出し中にエラーが発生しました: {e}。再試行します...",
                flush=True,
            )
            continue

    return translation


def _process_po_file(lang: str, po_file_path: str):
    """
    指定された言語の.poファイルを処理します。

    Args:
        lang (str): 翻訳対象の言語コード。
        po_file_path (str): 処理対象の.poファイルのパス。
    """
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

    # 翻訳が必要なエントリを処理
    untranslated_entries = po.untranslated_entries() + po.fuzzy_entries()

    for entry in tqdm(untranslated_entries, desc=f"{lang} の翻訳"):
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


def _cleanup_language_translation(lang: str):
    """
    特定の言語の不要な翻訳エントリを削除します。

    Args:
        lang (str): 処理対象の言語コード。
    """
    po_file_path = os.path.join(LOCALE_DIR, lang, "LC_MESSAGES", "messages.po")

    try:
        with open(po_file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        with open(po_file_path, "w", encoding="utf-8") as f:
            for line in lines:
                if not line.startswith("#~ "):
                    f.write(line)
        print(f"{lang} の不要な翻訳を削除しました。", flush=True)
    except Exception as e:
        print(f"{lang} の翻訳削除中にエラーが発生しました: {e}", flush=True)


def translate():
    """
    翻訳プロセスを自動化する関数（ローカル環境専用）。

    本番環境では翻訳機能を無効化しているため、
    この関数はローカル環境でのみ使用されます。
    """
    if not API_KEY:
        print("GEMINI_API_KEY環境変数が設定されていません。翻訳をスキップします。")
        return

    print("同期翻訳処理を開始します...", flush=True)

    # テンプレートファイルの生成
    print("テンプレートファイルを生成中...", flush=True)
    os.system(f"cd {BASE_DIR} && pybabel extract -F {CONFIG_FILE} -o {POT_FILE} .")

    print("翻訳ファイルをマージ中...", flush=True)
    os.system(f"cd {BASE_DIR} && pybabel update -i {POT_FILE} -d {LOCALE_DIR}")

    # 各言語の翻訳処理
    for lang in LANGUAGES:
        po_file_path = os.path.join(LOCALE_DIR, lang, "LC_MESSAGES", "messages.po")

        # ファイルが存在しない場合は新規作成
        if not os.path.exists(po_file_path):
            os.system(
                f"cd {BASE_DIR} && pybabel init -i {POT_FILE} -d {LOCALE_DIR} -l {lang}"
            )

        # 翻訳処理を実行
        _process_po_file(lang, po_file_path)

    # 翻訳ファイルのコンパイル
    print("翻訳ファイルをコンパイル中...", flush=True)
    os.system(f"cd {BASE_DIR} && pybabel compile -d {LOCALE_DIR}")

    print("不要な翻訳を削除中...", flush=True)
    for lang in LANGUAGES:
        _cleanup_language_translation(lang)

    print("翻訳が完了しました！", flush=True)


def add_country_translation():
    """
    database/countries.csvに、LANGUAGES で指定された言語コードごとの国名翻訳列を追加します。

    英語の国名を基準として、各対象言語に翻訳した国名列を追加します。
    既に該当言語の列が存在する場合はスキップし、存在しない場合のみ
    Gemini AIを使用して翻訳を実行します。

    処理の流れ：
    1. countries.csvファイルを読み込み
    2. 各言語について列の存在を確認
    3. 存在しない列については新規作成
    4. 英語列（"en"）の国名を各言語に翻訳
    5. 翻訳結果をCSVファイルに保存

    Note:
        - 翻訳元は "en" 列の国名です。
        - 国名が "-" の場合は翻訳せずにそのまま保持します。
        - 各言語の翻訳には進捗バーが表示されます。
        - エラーが発生した場合は処理を中断します。

    Raises:
        FileNotFoundError: countries.csvファイルが見つからない場合。
        pd.errors.EmptyDataError: CSVファイルが空の場合。
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

                # Gemini AIを使って国名を翻訳
                target_lang_name = LANG_NAMES.get(language, language)
                country_df.at[index, language] = gemini_translate(
                    text=en_country_name,
                    target_lang=target_lang_name,
                )

            # 新しい列を追加したデータフレームを保存
            country_df.to_csv(country_csv, index=False, encoding="utf-8")


if __name__ == "__main__":
    translate()
    add_country_translation()
