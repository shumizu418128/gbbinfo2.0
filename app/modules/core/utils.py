"""
コアユーティリティ関数モジュール
アプリケーション全体で使用される基本的な汎用関数を提供
"""

import os
from datetime import datetime
from functools import lru_cache

from app.modules.optimization.cache import persistent_cache

from ..config import AVAILABLE_YEARS


def get_current_timestamp():
    """
    現在時刻を取得して最終更新日時として使用する文字列を生成します。

    Returns:
        tuple: (DT_NOW, LAST_UPDATED) のタプル
    """
    dt_now = datetime.now()
    last_updated = "UPDATE " + dt_now.strftime("%Y/%m/%d %H:%M:%S") + " JST"
    return dt_now, last_updated


@lru_cache(maxsize=32)
def get_template_contents(year: int) -> list:
    """
    指定された年度のテンプレートコンテンツ一覧をキャッシュ機能付きで取得します。
    rule, world_mapテンプレートは除外されます。

    Args:
        year (int): 取得する年度

    Returns:
        list: テンプレートファイル名のリスト（拡張子なし）。
              ディレクトリが存在しない場合は空のリストを返します。
    """
    templates_dir_path = os.path.join(".", "app", "templates", str(year))
    contents = os.listdir(templates_dir_path)
    contents = [content.replace(".html", "") for content in contents]

    # rule, world_mapは除外
    contents = [c for c in contents if c not in ["rule", "world_map"]]
    return contents


@lru_cache(maxsize=1)
def get_others_templates() -> list:
    """
    othersディレクトリのテンプレート一覧をキャッシュ機能付きで取得します。

    Returns:
        list: othersテンプレートファイル名のリスト（拡張子なし）。
              ディレクトリが存在しない場合は空のリストを返します。
    """
    others_templates_path = os.path.join(".", "app", "templates", "others")
    contents = os.listdir(others_templates_path)
    return [content.replace(".html", "") for content in contents]


def is_latest_year(year):
    """
    指定された年度が最新年度または今年であるかを判定します。

    Args:
        year (int): 判定する年度

    Returns:
        bool: 最新年度または今年の場合はTrue、それ以外はFalse
    """
    dt_now = datetime.now()
    now = dt_now.year
    return year == max(AVAILABLE_YEARS) or year == now


def is_early_access(year):
    """
    指定された年度が、試験公開年度かを判定します。

    Args:
        year (int): 判定する年度

    Returns:
        bool: 試験公開年度の場合はTrue、それ以外はFalse
    """
    dt_now = datetime.now()
    now = dt_now.year
    return year > now


def is_translated(url, target_lang=None, translated_paths=None):
    """
    POファイルを読み込んで、指定されたページに翻訳が提供されているかをチェックします。

    Args:
        url (str): ページの内部URL
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
        translated_paths = persistent_cache.get_translated_paths()

    return url in translated_paths


def load_template_combinations_optimized():
    """
    サイトマップ生成のため全年度の組み合わせを取得します。

    Returns:
        list: (年度, コンテンツ名) のタプルのリスト
    """
    combinations = []

    # 全年度の組み合わせを取得（サイトマップ生成用）
    for year in AVAILABLE_YEARS:
        contents = get_template_contents(year)
        for content in contents:
            combinations.append((year, content))

    # 年度とコンテンツ名のリストを取得
    COMBINATIONS_YEAR = [year for year, _ in combinations]
    COMBINATIONS_CONTENT = [content for _, content in combinations]

    return (COMBINATIONS_YEAR, COMBINATIONS_CONTENT)


def get_categories_for_year(year, valid_categories_dict):
    """
    指定された年度のカテゴリを取得します（遅延読み込み対応）。

    Args:
        year (int): 取得する年度
        valid_categories_dict (dict): カテゴリのキャッシュ辞書

    Returns:
        list: 該当年度のカテゴリリスト
    """
    if year in valid_categories_dict:
        return valid_categories_dict[year]

    # 遅延読み込み：永続的キャッシュから取得
    categories = persistent_cache.get_categories(year)
    valid_categories_dict[year] = categories  # メモリキャッシュに保存
    return categories


def get_result_categories_for_year(year, all_category_dict):
    """
    指定された年度の結果カテゴリを取得します（遅延読み込み対応）。

    Args:
        year (int): 取得する年度
        all_category_dict (dict): 結果カテゴリのキャッシュ辞書

    Returns:
        list: 該当年度の結果カテゴリリスト
    """
    if year in all_category_dict:
        return all_category_dict[year]

    # 遅延読み込み：まだ読み込まれていない年度のデータを取得
    categories = persistent_cache.get_result_categories(year)
    all_category_dict[year] = categories  # キャッシュに保存
    return categories


def find_others_url(response_url, others_links):
    """
    レスポンスURLがothersリンクに含まれるかチェックし、適切なURLに変換します。

    Args:
        response_url (str): チェックするレスポンスURL
        others_links (list): othersリンクのリスト

    Returns:
        str | None: 変換されたURL、該当しない場合はNone
    """
    for link in others_links:
        clean_link = link.replace(".html", "")
        if clean_link in response_url:
            return f"/others/{clean_link}"
    return None
