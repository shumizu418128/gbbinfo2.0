from datetime import datetime

from app.participants import create_world_map, get_participants_list, get_results
from flask import Flask, redirect, render_template, request, url_for
from flask_caching import Cache

from app import key

app = Flask(__name__)
app.secret_key = key.SECRET_KEY


# Redisキャッシュの設定
# TODO: localの設定のままなので、本番環境では変更が必要
config = {
    "CACHE_TYPE": "RedisCache",
    "CACHE_REDIS_HOST": "localhost",
    "CACHE_REDIS_PORT": 6379,
    "CACHE_REDIS_DB": 0,
    "CACHE_REDIS_URL": "redis://localhost:6379/0",
    "CACHE_DEFAULT_TIMEOUT": 60 * 60  # 1時間（秒単位）
}
app.config.from_mapping(config)

cache = Cache(app)


# カスタムキャッシュキーの生成
def make_cache_key(*args, **kwargs):
    path = request.path
    args = str(hash(frozenset(request.args.items())))
    return f'{path}?{args}'


# /(年度) にアクセスしたときの処理
@app.route("/")
# @cache.cached()
def route_top():
    year = datetime.now().year
    content = 'top'
    return redirect(url_for("content", year=year, content=content))


# 世界地図の表示
@app.route('/<int:year>/world_map')
# @cache.cached()
def world_map(year: int = None):

    # 世界地図作成
    create_world_map(year)

    return render_template(f'{year}/world_map.html')


@app.route('/<int:year>/participants', methods=["GET"])
# @cache.cached(key_prefix=make_cache_key)
def participants(year: int = None):

    category = request.args.get("category")
    ticket_class = request.args.get("ticket_class")

    if category is None or ticket_class is None:
        if category is None:
            category = "Solo"
        if ticket_class is None:
            ticket_class = "all"
        return redirect(url_for('participants', year=year, category=category, ticket_class=ticket_class))

    # 参加者リストを取得
    participants_list = get_participants_list(year, category, ticket_class)

    return render_template(f"/{year}/participants.html", participants=participants_list, year=year)


@app.route("/<int:year>/result")
# @cache.cached()
def result(year: int = None):

    # 結果を取得
    results = get_results(year)

    return render_template(f"/{year}/result.html", results=results, year=year)


@app.route("/<int:year>/<string:content>")
# @cache.cached()
def content(year: int = None, content: str = None):

    if year is None:
        year = datetime.now().year

    available_years = [2023, 2024]
    if year not in available_years:
        year = 2024

    if content == "participants":
        return redirect(url_for("participants", year=year))

    if content == "result":
        return redirect(url_for("result", year=year))

    try:
        return render_template(f"/{year}/{content}.html", year=year)

    # エラーが出たらroute_topにリダイレクト
    except Exception as e:
        print(e)
        return redirect(url_for("route_top"))


if __name__ == "__main__":
    app.run(debug=True)
