import asyncio
import json
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

import google.generativeai as genai
import pandas as pd
import polib
from limits import RateLimitItemPerSecond
from limits.storage import MemoryStorage
from limits.strategies import FixedWindowRateLimiter
from tqdm import tqdm

from .config import create_safety_settings

SAFETY_SETTINGS = create_safety_settings("BLOCK_NONE")

# limitsによるレートリミット制御の初期化
storage = MemoryStorage()
rate_limit = RateLimitItemPerSecond(0.5)  # 2秒に1回
limiter = FixedWindowRateLimiter(storage)


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

# 非同期処理用のThreadPoolExecutor
_executor: Optional[ThreadPoolExecutor] = None

# レートリミット制御用のロック
_rate_limit_lock = None
_last_api_call_time = 0
RATE_LIMIT_INTERVAL = 2  # Geminiのレートリミット（2秒）に余裕を持たせる


def get_executor():
    """
    グローバルなThreadPoolExecutorを取得または作成します。

    非同期翻訳処理で使用するThreadPoolExecutorのインスタンスを管理します。
    レートリミット対策のため、最大1ワーカーに制限しています。

    Returns:
        ThreadPoolExecutor: 非同期処理用のThreadPoolExecutorインスタンス。
                           レートリミット遵守のため1つのワーカーで順次処理を実行します。
    """
    global _executor
    if _executor is None:
        # Gemini APIレートリミット（2秒に1回）を確実に順守するため、max_workers=1に設定
        # これにより全ての翻訳処理が単一スレッドで順次実行され、レートリミットが守られる
        _executor = ThreadPoolExecutor(max_workers=1)
    return _executor


def get_rate_limit_lock():
    """
    グローバルなレートリミット制御用のロックを取得または作成します。

    Returns:
        threading.Lock: レートリミット制御用のロックインスタンス。
    """
    global _rate_limit_lock
    if _rate_limit_lock is None:
        import threading

        _rate_limit_lock = threading.Lock()
    return _rate_limit_lock


def cleanup_executor():
    """
    ThreadPoolExecutorをクリーンアップします。

    グローバルなThreadPoolExecutorを安全にシャットダウンし、
    リソースを解放します。処理の完了を待たずに即座にシャットダウンします。

    Note:
        この関数は通常、アプリケーションの終了時やバックグラウンド翻訳処理の
        完了時に呼び出されます。
    """
    global _executor, _rate_limit_lock
    if _executor is not None:
        _executor.shutdown(wait=False)
        _executor = None
    _rate_limit_lock = None


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
    Google Gemini AIを使用してテキストを指定された言語に翻訳します。

    プレースホルダー（{変数名}形式）を保持しながら翻訳を行い、
    翻訳後のテキストでプレースホルダーが正しく維持されているかを検証します。
    検証に失敗した場合は再翻訳を実行します。

    Args:
        text (str): 翻訳するテキスト。プレースホルダーを含む可能性があります。
        target_lang (str): 翻訳先の言語名（例: "English", "French", "German"）。

    Returns:
        str: 翻訳されたテキスト。元のテキストのプレースホルダーが保持されます。

    Note:
        - limitsライブラリによるレートリミット制御（2秒に1回）を厳密に順守します。
        - プレースホルダーの検証に失敗した場合は自動的に再翻訳を実行します。
        - ThreadPoolExecutor(max_workers=1)との組み合わせで確実なレート制御を実現します。
    """
    while True:
        # limitsによるレートリミット制御（2秒に1回）
        while not limiter.hit(rate_limit, "gemini_api"):
            print("Gemini APIレートリミット待機中（2秒に1回制限）...", flush=True)
            time.sleep(0.5)

        try:
            # geminiに翻訳を依頼
            chat = model.start_chat()
            response = chat.send_message(prompt.format(lang=target_lang, source_text=text))
            translation = response.text.replace("\n", "")

            # プレースホルダーの検証
            result = validate_placeholders(text, translation)
            if not result:
                print(
                    f"プレースホルダーが一致しません。再翻訳します。元の文字列: {text}、翻訳後の文字列: {translation}",
                    flush=True,
                )
                # 再翻訳の場合もレートリミットを適用
                continue
            else:
                # プレースホルダーが一致する場合は翻訳完了
                break
        except Exception as e:
            print(f"Gemini API呼び出し中にエラーが発生しました: {e}。再試行します...", flush=True)
            # エラーの場合もレートリミットを適用してリトライ
            continue

    return translation


async def async_gemini_translate(text: str, target_lang: str):
    """
    非同期版のGemini翻訳関数です。

    同期版のgemini_translate関数をThreadPoolExecutorを使用して
    非同期実行します。これにより、複数の翻訳を並行して処理できます。

    Args:
        text (str): 翻訳するテキスト。プレースホルダーを含む可能性があります。
        target_lang (str): 翻訳先の言語名（例: "English", "French", "German"）。

    Returns:
        str: 翻訳されたテキスト。元のテキストのプレースホルダーが保持されます。

    Note:
        - 内部的にgemini_translate関数を別スレッドで実行します。
        - 複数の翻訳を並行処理する際のパフォーマンス向上に寄与します。
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        get_executor(), gemini_translate, text, target_lang
    )


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
    翻訳プロセスを自動化する関数（同期版）。

    この関数は以下のステップを実行します:
    1. テンプレートファイル (.pot) を再生成します。
    2. 既存の翻訳ファイル (.po) をテンプレートファイルとマージします。
    3. 未翻訳のエントリを Google Translate で翻訳します。
    4. 翻訳された内容で翻訳ファイルを更新します。
    5. 翻訳ファイルをコンパイルして、実行時に使用できる形式にします。

    ローカルでの実行を前提としています。
    """
    print("同期翻訳処理を開始します...", flush=True)

    # 共通の前処理
    _prepare_translation_files()

    # 各言語の翻訳処理（同期版）
    for lang in LANGUAGES:
        po_file_path = os.path.join(LOCALE_DIR, lang, "LC_MESSAGES", "messages.po")

        # ファイルが存在しない場合は新規作成
        if not os.path.exists(po_file_path):
            os.system(
                f"cd {BASE_DIR} && pybabel init -i {POT_FILE} -d {LOCALE_DIR} -l {lang}"
            )

        # 翻訳処理を実行
        _process_po_file(lang, po_file_path)

    # 共通の後処理
    _finalize_translation()

    print("翻訳が完了しました！", flush=True)


def _prepare_translation_files():
    """
    翻訳ファイルの準備処理を実行します。

    以下の処理を実行します:
    1. テンプレートファイル (.pot) を再生成
    2. 既存の翻訳ファイル (.po) をテンプレートファイルとマージ

    Note:
        - 同期版・非同期版共通の前処理です。
    """
    print("テンプレートファイルを生成中...", flush=True)
    os.system(f"cd {BASE_DIR} && pybabel extract -F {CONFIG_FILE} -o {POT_FILE} .")

    print("翻訳ファイルをマージ中...", flush=True)
    os.system(f"cd {BASE_DIR} && pybabel update -i {POT_FILE} -d {LOCALE_DIR}")


async def _async_prepare_translation_files():
    """
    翻訳ファイルの準備処理を非同期で実行します。

    以下の処理を実行します:
    1. テンプレートファイル (.pot) を再生成
    2. 既存の翻訳ファイル (.po) をテンプレートファイルとマージ

    Note:
        - 非同期版の前処理です。
    """
    print("テンプレートファイルを生成中...", flush=True)
    await asyncio.create_subprocess_shell(
        f"cd {BASE_DIR} && pybabel extract -F {CONFIG_FILE} -o {POT_FILE} ."
    )

    print("翻訳ファイルをマージ中...", flush=True)
    await asyncio.create_subprocess_shell(
        f"cd {BASE_DIR} && pybabel update -i {POT_FILE} -d {LOCALE_DIR}"
    )


def _finalize_translation():
    """
    翻訳処理の後処理を実行します。

    以下の処理を実行します:
    1. 翻訳ファイルのコンパイル (.mo形式)
    2. 不要な翻訳エントリの削除

    Note:
        - 同期版・非同期版共通の後処理です。
    """
    print("翻訳ファイルをコンパイル中...", flush=True)
    os.system(f"cd {BASE_DIR} && pybabel compile -d {LOCALE_DIR}")

    print("不要な翻訳を削除中...", flush=True)
    for lang in LANGUAGES:
        _cleanup_language_translation(lang)


async def _async_finalize_translation():
    """
    翻訳処理の後処理を非同期で実行します。

    以下の処理を実行します:
    1. 翻訳ファイルのコンパイル (.mo形式)
    2. 不要な翻訳エントリの削除

    Note:
        - 非同期版の後処理です。
    """
    print("翻訳ファイルをコンパイル中...", flush=True)
    await asyncio.create_subprocess_shell(
        f"cd {BASE_DIR} && pybabel compile -d {LOCALE_DIR}"
    )

    print("不要な翻訳を削除中...", flush=True)
    await _async_cleanup_translations()


async def async_translate():
    """
    非同期版翻訳プロセス。

    起動時の軽量化のために、重い翻訳処理を非同期で実行します。
    本番環境でstart_background_translation()から呼び出されます。

    Note:
        - Gemini API翻訳が完了してから後処理を実行するように順序を制御しています。
        - レートリミット（2秒に1回）を順守するため、ThreadPoolExecutor(max_workers=1)を使用。
        - 実際のAPI呼び出しはlimitsライブラリで厳密に制御されています。
    """
    print("非同期翻訳処理を開始します...", flush=True)

    # 共通の前処理（非同期版）
    await _async_prepare_translation_files()

    # 各言語の翻訳処理を並行実行
    # 注意: max_workers=1により、実際は順次実行でレートリミットを順守
    tasks = []
    for lang in LANGUAGES:
        task = asyncio.create_task(_async_translate_language(lang))
        tasks.append(task)

    # 全ての言語の翻訳を並行実行し、完了を待機
    print("Gemini API翻訳処理を開始します（レートリミット: 2秒に1回）...", flush=True)
    await asyncio.gather(*tasks)
    print("Gemini API翻訳処理が完了しました。後処理を開始します...", flush=True)

    # 共通の後処理（非同期版）- 翻訳完了後に実行
    await _async_finalize_translation()

    print("非同期翻訳が完了しました！", flush=True)


async def _async_translate_language(lang: str):
    """
    特定の言語に対する翻訳処理を非同期で実行します。

    指定された言語の.poファイルの処理を別スレッドで実行し、
    複数の言語を並行して翻訳処理できるようにします。

    Args:
        lang (str): 翻訳対象の言語コード（例: "en", "fr", "de"）。

    Note:
        - ファイルが存在しない場合は自動的に新規作成します。
        - 実際の翻訳処理は_process_po_file関数に委譲されます。
    """
    po_file_path = os.path.join(LOCALE_DIR, lang, "LC_MESSAGES", "messages.po")

    # ファイルが存在しない場合は新規作成
    if not os.path.exists(po_file_path):
        await asyncio.create_subprocess_shell(
            f"cd {BASE_DIR} && pybabel init -i {POT_FILE} -d {LOCALE_DIR} -l {lang}"
        )

    # poファイルの処理を別スレッドで実行
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(get_executor(), _process_po_file, lang, po_file_path)


def _process_po_file(lang: str, po_file_path: str):
    """
    指定された言語の.poファイルを処理します（同期処理）。

    以下の処理を実行します：
    1. 既存翻訳のプレースホルダー検証
    2. プレースホルダーが不正な翻訳にfuzzyフラグを付与
    3. 未翻訳エントリとfuzzyエントリの翻訳
    4. 翻訳完了後のfuzzyフラグ削除

    Args:
        lang (str): 翻訳対象の言語コード（例: "en", "fr", "de"）。
        po_file_path (str): 処理対象の.poファイルのパス。

    Note:
        - この関数は_async_translate_language関数から別スレッドで呼び出されます。
        - プレースホルダーの整合性を重視した翻訳処理を行います。
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


async def _async_cleanup_translations():
    """
    すべての言語の不要な翻訳エントリを非同期で削除します。

    各言語の.poファイルから、コメントアウトされた不要な翻訳エントリ
    （"#~ "で始まる行）を並行して削除します。

    Note:
        - 各言語の処理は並行実行され、処理時間を短縮します。
        - _cleanup_language_translation関数を各言語に対して並行実行します。
    """
    loop = asyncio.get_event_loop()
    tasks = []

    for lang in LANGUAGES:
        task = loop.run_in_executor(get_executor(), _cleanup_language_translation, lang)
        tasks.append(task)

    await asyncio.gather(*tasks)


def _cleanup_language_translation(lang: str):
    """
    特定の言語の不要な翻訳エントリを削除します。

    指定された言語の.poファイルから、コメントアウトされた
    不要な翻訳エントリ（"#~ "で始まる行）を削除します。

    Args:
        lang (str): 処理対象の言語コード（例: "en", "fr", "de"）。

    Note:
        - ファイルの読み書きエラーが発生した場合は、エラーメッセージを出力します。
        - この関数は_async_cleanup_translations関数から並行実行されます。
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


def start_background_translation():
    """
    バックグラウンドで翻訳処理を開始する関数です。

    アプリケーションの起動時間を短縮するため、翻訳処理を
    デーモンスレッドでバックグラウンド実行します。

    Returns:
        threading.Thread: 翻訳処理を実行するバックグラウンドスレッド。

    Note:
        - 処理完了後は自動的にThreadPoolExecutorをクリーンアップします。
        - エラーが発生した場合はエラーメッセージを出力しますが、
          アプリケーションの動作には影響しません。
        - デーモンスレッドとして実行されるため、メインプロセス終了時に
          自動的に終了します。
    """

    def run_async_translate():
        try:
            asyncio.run(async_translate())
        except Exception as e:
            print(f"バックグラウンド翻訳中にエラーが発生しました: {e}", flush=True)
        finally:
            cleanup_executor()

    # バックグラウンドスレッドで実行
    import threading

    thread = threading.Thread(target=run_async_translate, daemon=True)
    thread.start()
    return thread


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
