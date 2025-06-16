"""
永続的キャッシュ処理モジュール
起動時の重い処理を最適化するための永続的キャッシュシステムを提供
"""

import os
import pickle
import re
from typing import Any, Optional

import pandas as pd


class PersistentCache:
    """
    永続的キャッシュを管理するクラス。
    CSVデータ、カテゴリ情報、翻訳情報などを効率的にキャッシュし、
    アプリケーションの起動速度とレスポンス速度を向上させます。

    Attributes:
        cache_dir (str): キャッシュファイルを保存するディレクトリパス
        memory_cache (dict): メモリ内キャッシュ用の辞書
    """

    def __init__(self, cache_dir: str = "cache"):
        """
        PersistentCacheクラスのコンストラクタ。
        キャッシュディレクトリを作成し、メモリキャッシュを初期化します。

        Args:
            cache_dir (str, optional): キャッシュディレクトリのパス。デフォルトは"cache"。

        Returns:
            None
        """
        self.cache_dir = cache_dir
        self.memory_cache = {}

        # キャッシュディレクトリを作成
        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir)

    def _get_cache_path(self, key: str) -> str:
        """
        指定されたキーに対応するキャッシュファイルのパスを取得します。
        入力を正規化し、キャッシュディレクトリ内に限定します。

        Args:
            key (str): キャッシュキー

        Returns:
            str: キャッシュファイルの完全パス

        Raises:
            ValueError: 正規化後のパスがキャッシュディレクトリ外の場合
        """
        normalized_key = os.path.normpath(f"{key}.pkl")
        full_path = os.path.join(self.cache_dir, normalized_key)
        if not full_path.startswith(os.path.abspath(self.cache_dir)):
            raise ValueError(f"Invalid cache key: {key}")
        return full_path

    def get(self, key: str) -> Any:
        """
        キャッシュからデータを取得します。
        メモリキャッシュを最優先し、一度キャッシュされたデータは永続的に使用します。

        Args:
            key (str): 取得するデータのキー

        Returns:
            Any: キャッシュされたデータ。キャッシュが存在しない場合はNoneを返します。
        """
        # メモリキャッシュから確認（最優先、ファイルは見ない）
        if key in self.memory_cache:
            return self.memory_cache[key]

        # メモリにない場合のみファイルキャッシュから読み込み
        cache_path = self._get_cache_path(key)
        if os.path.exists(cache_path):
            try:
                with open(cache_path, "rb") as f:
                    data = pickle.load(f)
                    # メモリにキャッシュして今後はファイルを見ない
                    self.memory_cache[key] = data
                    return data
            except Exception:
                # キャッシュファイルが破損している場合は削除
                os.remove(cache_path)

        return None

    def set(self, key: str, data: Any) -> None:
        """
        データをメモリキャッシュに保存し、永続化のためファイルにも保存します。

        Args:
            key (str): 保存するデータのキー
            data (Any): 保存するデータ

        Returns:
            None
        """
        # メモリキャッシュに保存（最優先）
        self.memory_cache[key] = data

        # ファイルキャッシュに保存（永続化のため）
        cache_path = self._get_cache_path(key)
        try:
            with open(cache_path, "wb") as f:
                pickle.dump(data, f)
        except Exception as e:
            print(f"キャッシュ保存エラー: {e}")

    def get_csv_data(self, year: int) -> Optional[pd.DataFrame]:
        """
        指定された年度のCSVデータを永続的キャッシュから取得します。
        キャッシュにない場合はファイルから読み込み、結果をキャッシュに保存します。

        Args:
            year (int): 取得する年度

        Returns:
            Optional[pd.DataFrame]: CSVデータのDataFrame。
                                   ファイルが存在しない場合は空のDataFrameを返します。
        """
        csv_path = os.path.join("app", "database", "participants", f"{year}.csv")
        cache_key = f"csv_{year}"

        # キャッシュから取得を試行
        cached_data = self.get(cache_key)
        if cached_data is not None:
            return cached_data

        # キャッシュにない場合は読み込み
        try:
            df = pd.read_csv(csv_path)
            df = df.fillna("")
            self.set(cache_key, df)
            return df
        except FileNotFoundError:
            empty_df = pd.DataFrame()
            self.set(cache_key, empty_df)
            return empty_df

    def get_categories(self, year: int) -> list:
        """
        指定された年度のカテゴリ一覧を永続的キャッシュから取得します。
        キャッシュにない場合はCSVデータから計算し、結果をキャッシュに保存します。

        Args:
            year (int): 取得する年度

        Returns:
            list: カテゴリ名のリスト。データが存在しない場合は空のリストを返します。
        """
        cache_key = f"categories_{year}"

        # キャッシュから取得を試行
        cached_categories = self.get(cache_key)
        if cached_categories is not None:
            return cached_categories

        # キャッシュにない場合はCSVから計算
        df = self.get_csv_data(year)
        if df.empty:
            categories = []
        else:
            categories = df["category"].unique().tolist()

        self.set(cache_key, categories)
        return categories

    def get_result_categories(self, year: int) -> list:
        """
        指定された年度の結果カテゴリ一覧を永続的キャッシュから取得します。
        キャッシュにない場合は結果ディレクトリから読み込み、結果をキャッシュに保存します。

        Args:
            year (int): 取得する年度

        Returns:
            list: 結果カテゴリ名のリスト（Loopstation, Producerが先頭に配置）。
                  ディレクトリが存在しない場合は空のリストを返します。
        """
        base_dir = os.path.join(".", "app", "database", "result")
        result_dir = os.path.normpath(os.path.join(base_dir, str(year)))

        # Validate that result_dir is within base_dir
        if not result_dir.startswith(os.path.abspath(base_dir)):
            raise ValueError(f"Invalid year parameter: {year}")

        cache_key = f"result_categories_{year}"

        # キャッシュから取得を試行
        cached_categories = self.get(cache_key)
        if cached_categories is not None:
            return cached_categories

        # キャッシュにない場合は読み込み
        try:
            all_category = os.listdir(result_dir)
            all_category = [category.replace(".csv", "") for category in all_category]

            # Loopstation, Producerを先頭に
            all_category.sort(
                key=lambda x: (x == "Loopstation", x == "Producer"),
                reverse=True,
            )
            self.set(cache_key, all_category)
            return all_category
        except Exception:
            empty_list = []
            self.set(cache_key, empty_list)
            return empty_list

    def get_translated_paths(self) -> set:
        """
        翻訳が存在するページのパス一覧を永続的キャッシュから取得します。
        キャッシュにない場合はPOファイルから解析し、結果をキャッシュに保存します。

        Returns:
            set: 翻訳されたページのパスセット。
                 POファイルが存在しない場合は空のセットを返します。
        """
        po_file_path = os.path.join(
            "app", "translations", "en", "LC_MESSAGES", "messages.po"
        )
        cache_key = "translated_paths"

        # キャッシュから取得を試行
        cached_paths = self.get(cache_key)
        if cached_paths is not None:
            return cached_paths

        # キャッシュにない場合は読み込み
        from .config import AVAILABLE_YEARS

        translated_paths = set()

        try:
            with open(po_file_path, "r", encoding="utf-8") as f:
                po_content = f.read()
        except FileNotFoundError:
            self.set(cache_key, translated_paths)
            return translated_paths

        exclude_words = [r":\d+", "templates/", ".html"]

        for line in po_content.split("\n"):
            if line.startswith("#: templates/"):
                paths = line.replace("#:", "").split()

                for path in paths:
                    # 除外条件
                    if any(
                        exclude in path
                        for exclude in [
                            "templates/base.html",
                            "templates/includes/",
                            "404.html",
                        ]
                    ):
                        continue

                    # パスの正規化
                    if path.startswith("templates/"):
                        for word in exclude_words:
                            path = re.sub(word, "", path)

                    # common/の場合は年度を追加
                    if path.startswith("common/"):
                        for year in AVAILABLE_YEARS:
                            formatted_path = f"/{year}/{path.replace('common/', '')}"
                            translated_paths.add(formatted_path)
                        continue

                    translated_paths.add("/" + path)

        self.set(cache_key, translated_paths)
        return translated_paths


# グローバルインスタンス
persistent_cache = PersistentCache()
