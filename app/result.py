import pandas as pd


def get_result(category: str, year: int):
    """
    指定されたカテゴリと年の結果を取得します。

    Args:
        category (str): カテゴリ。
        year (int): 年。

    Returns:
        dict: 結果の辞書。
    """
    try:
        df = pd.read_csv(f'app/static/csv/result/{year}/{category}.csv')
    except FileNotFoundError:
        return None

    result_dict = {}

    # 辞書を作成
    for _, row in df.iterrows():
        round_name = row['round']
        win = row['win']
        lose = row['lose']

        # ラウンド名がキーになっているリストに追加
        if round_name not in result_dict:
            result_dict[round_name] = []

        result_dict[round_name].append({
            'win': win,
            'lose': lose
        })

    return result_dict
