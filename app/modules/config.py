import os

# 利用可能な年度と言語のリスト
available_years = [2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025]
available_langs = ["ja", "en", "zh_Hant_TW", "ko"]


# Flaskの設定
class Config:
    SECRET_KEY = os.getenv("SECRET_KEY")
    GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
    BABEL_DEFAULT_LOCALE = "ja"
    BABEL_SUPPORTED_LOCALES = available_langs
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
