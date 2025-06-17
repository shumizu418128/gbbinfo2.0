"""
年度バリデーション用のデコレータ

このモジュールでは、年度の有効性を検証するデコレータを提供します。
"""

from functools import wraps
from flask import abort, redirect, url_for
from ..config import AVAILABLE_YEARS


def validate_year(f):
    """
    年度の有効性を検証するデコレータ

    指定された年度がAVAILABLE_YEARSに含まれているかを確認し、
    含まれていない場合は404エラーを返します。
    2022年度の場合はトップページへリダイレクトします。

    Args:
        f (function): デコレートする関数

    Returns:
        function: デコレートされた関数

    Raises:
        abort(404): 年度が有効でない場合
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # 引数から年度を取得
        year = kwargs.get('year')
        if year is None and args:
            # 位置引数の最初の引数が年度の場合
            year = args[0]

        # 年度が有効でない場合は404エラー
        if year not in AVAILABLE_YEARS:
            abort(404)

        # 2022年度のリダイレクト処理
        if year == 2022:
            content = kwargs.get('content', "")
            if content != "top":
                return redirect(url_for("content", year=year, content="top"))

        return f(*args, **kwargs)

    return decorated_function
