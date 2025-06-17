"""
コアユーティリティ関数モジュール
アプリケーション全体で使用される基本的な汎用関数を提供
"""

import os
from datetime import datetime
from functools import lru_cache

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
    try:
        templates_dir_path = os.path.join(".", "app", "templates", str(year))
        contents = os.listdir(templates_dir_path)
        contents = [content.replace(".html", "") for content in contents]

        # rule, world_mapは除外
        contents = [c for c in contents if c not in ["rule", "world_map"]]
        return contents
    except OSError:
        return []


@lru_cache(maxsize=1)
def get_others_templates() -> list:
    """
    othersディレクトリのテンプレート一覧をキャッシュ機能付きで取得します。

    Returns:
        list: othersテンプレートファイル名のリスト（拡張子なし）。
              ディレクトリが存在しない場合は空のリストを返します。
    """
    try:
        others_templates_path = os.path.join(".", "app", "templates", "others")
        contents = os.listdir(others_templates_path)
        return [content.replace(".html", "") for content in contents]
    except OSError:
        return []


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


def load_template_combinations_optimized():
    """
    テンプレート組み合わせを最適化して読み込みます（起動速度重視）。
    最新2年度のテンプレートのみを起動時に読み込み、他の年度は遅延読み込みで対応します。

    Returns:
        list: (年度, コンテンツ名) のタプルのリスト
    """
    combinations = []
    # 最新2年度のみを優先読み込み
    priority_years = sorted(AVAILABLE_YEARS, reverse=True)[:2]

    for year in priority_years:
        contents = get_template_contents(year)
        for content in contents:
            combinations.append((year, content))

    return combinations
