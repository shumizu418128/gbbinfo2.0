import os

# 利用可能な年度と言語のリスト
AVAILABLE_YEARS = [2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025]
AVAILABLE_LANGS = ["ja", "en", "zh_Hant_TW", "ko", "zh_Hans_CN", "de", "ms", "id"]


# Flaskの設定
class Config:
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
    CACHE_TYPE = "null"
    DEBUG = True
    TEMPLATES_AUTO_RELOAD = True
    SECRET_KEY = "test"
