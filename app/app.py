import os

import requests

import jinja2
import pandas as pd
from flask import Flask, jsonify, redirect, render_template, request, send_file, url_for
from flask_caching import Cache
from flask_sitemapper import Sitemapper

from . import key
from .participants import create_world_map, get_japan_participants, get_participants_list, get_results

app = Flask(__name__)
sitemapper = Sitemapper()
sitemapper.init_app(app)
app.secret_key = os.getenv("SECRET_KEY")
github_token = os.getenv("GITHUB_TOKEN")
available_years = key.available_years

# テスト環境ではキャッシュを無効化
if os.getenv("SECRET_KEY") is None and os.getenv("GITHUB_TOKEN") is None:
    app.config['CACHE_TYPE'] = "null"
    cache = Cache(app, config={'CACHE_TYPE': 'null'})

# 本番環境ではキャッシュを有効化
else:
    app.config['CACHE_DEFAULT_TIMEOUT'] = 0  # 永続化
    cache = Cache(app, config={'CACHE_TYPE': 'filesystem', 'CACHE_DIR': 'cache-directory'})


# カスタムキャッシュキーの生成
def make_cache_key(*args):
    path = request.path
    args = str(hash(frozenset(request.args.items())))
    return f'{path}?{args}'


####################################################################
# /(年度) にアクセスしたときの処理
####################################################################
@app.route("/")
@cache.cached()
def route_top():

    # 最新年度を表示
    year = available_years[-1]

    return redirect(url_for("content", year=year, content="top"))


####################################################################
# 世界地図の表示
####################################################################
@app.route('/<int:year>/world_map')
@cache.cached()
def world_map(year: int = None):

    # 年度が指定されていない場合は最新年度を表示
    if year not in available_years:
        year = available_years[-1]

    # 世界地図作成
    create_world_map(year)

    return render_template(f'{year}/world_map.html')


####################################################################
# 出場者一覧
####################################################################
@sitemapper.include(changefreq="monthly", priority=1.0, url_variables={"year": available_years})
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

    # 結果URLを取得
    try:
        result_url = key.result[year][category]
    except KeyError:
        result_url = None

    return render_template("/participants.html", participants=participants_list, year=year, all_category=valid_categories, result_url=result_url)


####################################################################
# 日本代表
####################################################################
@sitemapper.include(changefreq="yearly", priority=0.8, url_variables={"year": available_years})
@app.route("/<int:year>/japan")
@cache.cached()
def japan(year: int = None):
    # 参加者リストを取得
    participants_list = get_japan_participants(year)

    return render_template("/japan.html", participants=participants_list, year=year)


####################################################################
# 大会結果
####################################################################
@sitemapper.include(changefreq="yearly", priority=0.8, url_variables={"year": available_years})
@app.route("/<int:year>/result")
@cache.cached()
def result(year: int = None):

    # 年度が指定されていない場合は最新年度を表示
    if year not in available_years:
        year = available_years[-1]

    # 結果を取得
    results = get_results(year)

    return render_template("/result.html", results=results, year=year)


####################################################################
# 各年度のページ
####################################################################

combinations = []

for year in available_years:
    contents = os.listdir(f"./app/templates/{year}")
    contents = [content.replace(".html", "") for content in contents]
    for content in contents:
        combinations.append((year, content))

combinations_year = [year for year, _ in combinations]
combinations_content = [content for _, content in combinations]


@sitemapper.include(changefreq="weekly", priority=0.8, url_variables={"year": combinations_year, "content": combinations_content})
@app.route("/<int:year>/<string:content>")
@cache.cached()
def content(year: int = None, content: str = None):

    # 年度が指定されていない場合は最新年度を表示
    if year not in available_years:
        year = available_years[-1]

    # その他のページはそのまま表示
    try:
        return render_template(f"/{year}/{content}.html", year=year)

    # エラーが出たらtopを表示
    except jinja2.exceptions.TemplateNotFound:
        return render_template("404.html"), 404


####################################################################
# その他のページ
####################################################################

content_others = os.listdir("./app/templates/others")
content_others = [content.replace(".html", "") for content in content_others]


@sitemapper.include(changefreq="never", priority=0.7, url_variables={"content": content_others})
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
# API
####################################################################

@app.route("/last-commit")
@cache.cached()
def get_last_commit():
    headers = {
        'Authorization': f'token {github_token}'
    }
    response = requests.get("https://api.github.com/repos/shumizu418128/gbbinfo2.0/commits", headers=headers)

    if response.status_code == 403:
        return jsonify({"error": "APIのレートリミットに達しました。しばらくしてから再試行してください。"}), 403

    if response.status_code != 200:
        return jsonify({"error": "データの取得に失敗しました"}), 500

    return jsonify(response.json())


####################################################################
# Sitemap, robots.txt
####################################################################

@app.route("/sitemap.xml")
def sitemap():
    return sitemapper.generate()


@app.route("/robots.txt")
def robots_txt():
    return send_file("robots.txt", mimetype="text/plain")


####################################################################
# favicon.ico
####################################################################

@app.route("/favicon.ico", methods=["GET"])
def favicon_ico():
    return send_file("favicon.ico", mimetype="image/vnd.microsoft.icon")


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
