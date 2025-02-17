from collections import defaultdict

import pandas as pd


def get_result(category: str, year: int):
    """
    指定されたカテゴリと年の結果を取得します。

    Args:
        category (str): カテゴリ。
        year (int): 年。

    Returns:
        list: 結果の種類と結果の辞書。
        - 結果の種類: "tournament" または "ranking"。
        - 結果の辞書: ラウンド名をキーにしたリスト。
            - トーナメント表の場合: ラウンドごとの勝敗を含む辞書。
            - ランキング表の場合: ラウンドごとの順位を含む辞書。
    """
    try:
        df = pd.read_csv(f"app/database/result/{year}/{category}.csv")
    except FileNotFoundError:
        return None

    # カラム名を取得
    columns = df.columns.tolist()
    result_dict = defaultdict(list)

    # トーナメント表の場合
    if "win" in columns:
        # 辞書を作成
        for _, row in df.iterrows():
            round_name = row["round"]
            win = row["win"].upper()  # CSV に記載されている名前を大文字に変換
            lose = row["lose"].upper()  # CSV に記載されている名前を大文字に変換

            # ラウンド名がキーになっているリストに追加
            result_dict[round_name].append({"win": win, "lose": lose})

        return ["tournament", result_dict]

    # ランキング表の場合
    elif "rank" in columns:
        for _, row in df.iterrows():
            round_name = row["round"]
            rank = row["rank"]
            name = row["name"].upper()  # CSV に記載されている名前を大文字に変換

            # ラウンド名がキーになっているリストに追加
            result_dict[round_name].append({"rank": rank, "name": name})

        return ["ranking", result_dict]

    # それ以外の場合
    raise ValueError("Invalid CSV file.")
