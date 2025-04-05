import os

# 利用可能な年度と言語のリスト
AVAILABLE_YEARS = [2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025]
LANG_NAMES = {
    "ja": "日本語",
    "en": "English",
    "zh_Hant_TW": "繁體中文",
    "ko": "한국어",
    "zh_Hans_CN": "简体中文",
    "de": "Deutsch",
    "ms": "Bahasa MY",
    "id": "Bahasa ID",
    "fr": "Français",
    "hu": "Magyar",
    "it": "Italiano",
    "hi": "हिन्दी",
}
AVAILABLE_LANGS = list(LANG_NAMES.keys())


# Flaskの設定
class Config:
    """Flaskアプリケーションの設定クラス。

    Attributes:
        SECRET_KEY (str): Flaskアプリケーションの秘密鍵。
        GITHUB_TOKEN (str): GitHub APIのトークン。
        BABEL_DEFAULT_LOCALE (str): Babelのデフォルトロケール。
        BABEL_SUPPORTED_LOCALES (list): Babelでサポートされるロケールのリスト。
        CACHE_TYPE (str): キャッシュの種類。
        CACHE_DIR (str): キャッシュディレクトリ。
        CACHE_DEFAULT_TIMEOUT (int): キャッシュのデフォルトタイムアウト。
        DEBUG (bool): デバッグモードの有効/無効。
        TEMPLATES_AUTO_RELOAD (bool): テンプレートの自動リロードの有効/無効。
    """
    SECRET_KEY = os.getenv("SECRET_KEY")
    GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
    BABEL_DEFAULT_LOCALE = "ja"
    BABEL_SUPPORTED_LOCALES = AVAILABLE_LANGS
    CACHE_TYPE = "filesystem"
    CACHE_DIR = "cache-directory"
    CACHE_DEFAULT_TIMEOUT = 0
    DEBUG = False
    TEMPLATES_AUTO_RELOAD = False


class TestConfig(Config):
    """テスト環境用の設定クラス。

    Configクラスを継承し、テストに特化した設定を行います。

    Attributes:
        CACHE_TYPE (str): キャッシュの種類を'null'に設定し、キャッシュを無効化します。
        DEBUG (bool): デバッグモードを有効にします。
        TEMPLATES_AUTO_RELOAD (bool): テンプレートの自動リロードを有効にします。
        SECRET_KEY (str): テスト用の秘密鍵を設定します。
    """
    CACHE_TYPE = "null"
    DEBUG = True
    TEMPLATES_AUTO_RELOAD = True
    SECRET_KEY = "test"
