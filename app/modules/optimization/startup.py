"""
起動速度最適化のためのモジュール
アプリケーション起動時の重い処理を並列化・最適化するための機能を提供
"""

import os
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from typing import Any, Dict, List

import pandas as pd

from ..config import AVAILABLE_YEARS
from .cache import persistent_cache


class StartupOptimizer:
    """
    起動時の重い処理を最適化するクラス。
    CSVファイルの並列読み込み、テンプレートファイルのキャッシュ、
    必要最小限のデータ事前読み込みなどを提供します。

    Attributes:
        csv_cache (dict): CSVデータのメモリキャッシュ
        template_cache (dict): テンプレートファイル一覧のキャッシュ
    """

    def __init__(self):
        """
        StartupOptimizerクラスのコンストラクタ。
        キャッシュ用の辞書を初期化します。

        Returns:
            None
        """
        self.csv_cache = {}
        self.template_cache = {}

    @lru_cache(maxsize=128)
    def get_csv_data(self, year: int) -> pd.DataFrame:
        """
        指定された年度のCSVデータをキャッシュ機能付きで読み込みます。
        一度読み込んだデータはメモリ内にキャッシュされ、以降の呼び出しで高速に返されます。

        Args:
            year (int): 読み込む年度

        Returns:
            pd.DataFrame: CSVデータのDataFrame。
                         ファイルが存在しない場合は空のDataFrameを返します。
        """
        if year in self.csv_cache:
            return self.csv_cache[year]

        csv_path = os.path.join("app", "database", "participants", f"{year}.csv")
        if os.path.exists(csv_path):
            df = pd.read_csv(csv_path)
            df = df.fillna("")
            self.csv_cache[year] = df
            return df
        return pd.DataFrame()

    def load_csvs_parallel(self, years: List[int]) -> Dict[int, pd.DataFrame]:
        """
        複数年度のCSVファイルを並列読み込みします。
        ThreadPoolExecutorを使用して最大4つのファイルを同時に処理し、
        I/O待機時間を短縮します。

        Args:
            years (List[int]): 読み込む年度のリスト

        Returns:
            Dict[int, pd.DataFrame]: 年度をキーとし、DataFrameを値とする辞書。
                                   読み込みに失敗した年度は空のDataFrameが設定されます。
        """
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {executor.submit(self.get_csv_data, year): year for year in years}
            results = {}
            for future in futures:
                year = futures[future]
                try:
                    results[year] = future.result()
                except Exception as e:
                    print(f"Error loading CSV for year {year}: {e}")
                    results[year] = pd.DataFrame()
        return results

    @lru_cache(maxsize=32)
    def get_template_files(self, directory: str) -> List[str]:
        """
        指定されたディレクトリのテンプレートファイル一覧をキャッシュ機能付きで取得します。
        一度読み込んだディレクトリ情報はキャッシュされ、以降の呼び出しで高速に返されます。

        Args:
            directory (str): テンプレートファイルが格納されているディレクトリパス

        Returns:
            List[str]: ディレクトリ内のファイル一覧。
                      ディレクトリが存在しない場合は空のリストを返します。
        """
        if directory in self.template_cache:
            return self.template_cache[directory]

        try:
            files = os.listdir(directory)
            self.template_cache[directory] = files
            return files
        except OSError:
            return []

    def preload_essential_data(self) -> Dict[str, Any]:
        """
        起動速度向上のため、必要最小限のデータを事前読み込みします。
        最新2年度のデータのみを優先的に読み込み、他の年度は遅延読み込みに委ねます。

        Returns:
            Dict[str, Any]: 事前読み込みされたデータを含む辞書。
                           以下のキーを含みます：
                           - csv_data: CSVデータの辞書
                           - categories: カテゴリ情報の辞書
                           - loaded_years: 読み込み済み年度のリスト
        """
        # 最新2年度のみを優先的に読み込み
        priority_years = sorted(AVAILABLE_YEARS, reverse=True)[:2]

        # 並列でCSVデータを読み込み
        csv_data = self.load_csvs_parallel(priority_years)

        # カテゴリ情報を事前計算
        categories_dict = {}
        for year, df in csv_data.items():
            if not df.empty:
                categories_dict[year] = df["category"].unique().tolist()

        return {
            "csv_data": csv_data,
            "categories": categories_dict,
            "loaded_years": priority_years,
        }


def load_csv_optimized(year: int) -> pd.DataFrame:
    """
    指定された年度のCSVファイルを永続的キャッシュ機能付きで読み込みます。

    Args:
        year (int): 読み込む年度

    Returns:
        pd.DataFrame: CSVデータのDataFrame。ファイルが存在しない場合は空のDataFrameを返します。
    """
    return persistent_cache.get_csv_data(year)


def load_categories_parallel():
    """
    カテゴリデータを最小限で読み込みます（起動速度重視）。
    最新2年度のデータのみを起動時に読み込み、他の年度は遅延読み込みで対応します。

    Returns:
        dict: 年度をキーとし、カテゴリリストを値とする辞書
    """
    categories_dict = {}

    # 最新2年度のみを起動時に読み込み
    priority_years = sorted(AVAILABLE_YEARS, reverse=True)[:2]

    for year in priority_years:
        categories_dict[year] = persistent_cache.get_categories(year)

    return categories_dict


def load_result_categories_optimized():
    """
    結果カテゴリを最小限で読み込みます（起動速度重視）。
    最新2年度のデータのみを起動時に読み込み、他の年度は遅延読み込みで対応します。

    Returns:
        dict: 年度をキーとし、結果カテゴリリストを値とする辞書
    """
    categories_dict = {}
    # 最新2年度のみを起動時に読み込み
    priority_years = sorted(AVAILABLE_YEARS, reverse=True)[:2]

    for year in priority_years:
        categories_dict[year] = persistent_cache.get_result_categories(year)

    return categories_dict


# グローバルインスタンス
startup_optimizer = StartupOptimizer()
