import os

import jinja2
import pandas as pd
from flask import Flask, redirect, render_template, request, send_file, url_for
from flask_caching import Cache
from flask_sitemap import Sitemap

from . import key
from .participants import create_world_map, get_participants_list, get_results

app = Flask(__name__)
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.secret_key = os.getenv("SECRET_KEY")
sitemap = Sitemap(app=app)
available_years = key.available_years

# キャッシュのデフォルトの有効期限を設定する
app.config['CACHE_DEFAULT_TIMEOUT'] = 60 * 60 * 24 * 30  # 30d
cache = Cache(app, config={'CACHE_TYPE': 'simple'})


# カスタムキャッシュキーの生成
def make_cache_key(*args):
    path = request.path
    args = str(hash(frozenset(request.args.items())))
    return f'{path}?{args}'


# /(年度) にアクセスしたときの処理
@app.route("/")
@cache.cached()
def route_top():

    # 最新年度を表示
    year = available_years[-1]

    return render_template(f"{year}/top.html", year=year)


# 世界地図の表示
@app.route('/<int:year>/world_map')
@cache.cached()
def world_map(year: int = None):

    # 年度が指定されていない場合は最新年度を表示
    if year not in available_years:
        year = available_years[-1]

    # 世界地図作成
    create_world_map(year)

    return render_template(f'{year}/world_map.html')


@app.route('/<int:year>/participants', methods=["GET"])
@cache.cached(key_prefix=make_cache_key)
def participants(year: int = None):

    # 年度が指定されていない場合は最新年度を表示
    if year not in available_years:
        year = available_years[-1]

    # categoryとticket_classを取得
    category = request.args.get("category")
    ticket_class = request.args.get("ticket_class")

    # categoryとticket_classが不正な場合はSolo全出場者を表示
    valid_categories = pd.read_csv(
        f'app/static/csv/gbb{year}_participants.csv')["category"].unique()
    valid_ticket_classes = ["wildcard", "seed_right", "all"]
    valid = all([
        category in valid_categories,
        ticket_class in valid_ticket_classes
    ])

    if valid is False:
        return redirect(url_for('participants', year=year, category="Solo", ticket_class="all"))

    # 参加者リストを取得
    participants_list = get_participants_list(year, category, ticket_class)

    return render_template("/participants.html", participants=participants_list, year=year, all_category=valid_categories)


@app.route("/<int:year>/result")
@cache.cached()
def result(year: int = None):

    # 年度が指定されていない場合は最新年度を表示
    if year not in available_years:
        year = available_years[-1]

    # 結果を取得
    results = get_results(year)

    return render_template("/result.html", results=results, year=year)


@app.route("/<int:year>/<string:content>")
@cache.cached()
def content(year: int = None, content: str = None):

    # 年度が指定されていない場合は最新年度を表示
    if year not in available_years:
        year = available_years[-1]

    # participants, resultは専用のページにリダイレクト
    if content == "participants":
        return redirect(url_for("participants", year=year))

    if content == "result":
        return redirect(url_for("result", year=year))

    # その他のページはそのまま表示
    try:
        return render_template(f"/{year}/{content}.html", year=year)

    # エラーが出たらtopを表示
    except jinja2.exceptions.TemplateNotFound:
        return render_template("404.html"), 404


@app.route("/others/<string:content>")
@cache.cached()
def others(content: str = None):

    year = available_years[-1]

    try:
        return render_template(f"/others/{content}.html", year=year)

    # エラー
    except jinja2.exceptions.TemplateNotFound:
        return render_template("404.html"), 404


####################################################################
# PWS設定
####################################################################

@app.route("/manifest.json")
def manifest():
    return send_file('manifest.json', mimetype='application/manifest+json')


@app.route("/service-worker.js")
def service_worker():
    return send_file('service-worker.js', mimetype='application/javascript')


####################################################################
# エラーハンドラ
####################################################################


@app.errorhandler(404)
def page_not_found(_):
    return render_template("404.html"), 404


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
