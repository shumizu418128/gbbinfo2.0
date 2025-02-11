import os

import polib
from googletrans import Translator


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
    BASE_DIR = os.path.abspath("app")
    LOCALE_DIR = os.path.join(BASE_DIR, "translations")
    POT_FILE = os.path.join(BASE_DIR, "messages.pot")
    CONFIG_FILE = os.path.join(BASE_DIR, "babel.cfg")
    LANGUAGES = [
        d for d in os.listdir(LOCALE_DIR) if os.path.isdir(os.path.join(LOCALE_DIR, d))
    ]

    # 1. テンプレートファイルの再生成
    os.system(f"cd {BASE_DIR} && pybabel extract -F {CONFIG_FILE} -o {POT_FILE} .")

    # 2. 翻訳ファイルのマージ
    os.system(f"cd {BASE_DIR} && pybabel update -i {POT_FILE} -d {LOCALE_DIR}")

    # 3. 未翻訳部分を googletrans で翻訳
    translator = Translator()

    for lang in LANGUAGES:
        po_file_path = os.path.join(LOCALE_DIR, lang, "LC_MESSAGES", "messages.po")

        if not os.path.exists(po_file_path):
            print(f"{po_file_path} が存在しません。スキップします。")
            continue  # .po ファイルがない場合はスキップ

        po = polib.pofile(po_file_path)
        for entry in po.untranslated_entries():
            try:
                translation = translator.translate(
                    entry.msgid, src="en", dest=lang.split("_")[0]
                ).text
                entry.msgstr = translation
            except Exception as e:
                print(f"{lang} の翻訳中にエラーが発生しました: {e}")
                continue

        po.save(po_file_path)
        print(f"{lang} の翻訳を保存しました。", flush=True)

    # 4. 再コンパイル
    os.system(f"cd {BASE_DIR} && pybabel compile -d {LOCALE_DIR}")

    print("翻訳が完了しました！", flush=True)


if __name__ == "__main__":
    translate()
