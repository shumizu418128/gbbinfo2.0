import os
import warnings
from datetime import datetime

import jinja2
import pandas as pd
import requests
from flask import (Flask, jsonify, redirect, render_template, request,
                   send_file, url_for)
from flask_caching import Cache
from flask_sitemapper import Sitemapper

from . import gemini, key, spreadsheet
from .participants import (create_world_map, get_participants_list,
                           get_results, search_participants)

app = Flask(__name__)
sitemapper = Sitemapper()
sitemapper.init_app(app)
app.secret_key = os.getenv("SECRET_KEY")
github_token = os.getenv("GITHUB_TOKEN")
available_years = key.available_years

# 質問例を読み込む
example_questions = spreadsheet.get_example_questions()

# 現在時刻を読み込む(最終更新日時として使用)
dt_now = datetime.now()
last_updated = "最終更新：" + dt_now.strftime("%Y/%m/%d %H:%M:%S")

# 特定の警告を無視
warnings.filterwarnings(
    "ignore",
    category=UserWarning,
    message="Flask-Caching: CACHE_TYPE is set to null, caching is effectively disabled."
)
# テスト環境ではキャッシュを無効化
# ローカル環境にはこの環境変数を設定してある
if os.getenv("ENVIRONMENT_CHECK") == "qawsedrftgyhujikolp":
    print("\nくぁwせdrftgyふじこlp\n")
    app.config['CACHE_TYPE'] = "null"
    app.config['DEBUG'] = True
    app.config['TEMPLATES_AUTO_RELOAD'] = True
    cache = Cache(app, config={'CACHE_TYPE': 'null'})

# 本番環境ではキャッシュを有効化
else:
    app.config['CACHE_DEFAULT_TIMEOUT'] = 0  # 永続化
    cache = Cache(
        app, config={
            'CACHE_TYPE': 'filesystem',
            'CACHE_DIR': 'cache-directory'
        }
    )


# 最新年度かを判定
# 今年 or 最新年度のみTrue
def is_latest_year(year):
    """
    指定された年度が最新年度または今年であるかを判定します。

    :param year: 判定する年度
    :return: 最新年度または今年の場合はTrue、それ以外はFalse
    """
    dt_now = datetime.now()
    now = dt_now.year
    return year == available_years[-1] or year == now


def is_early_access(year):
    """
    指定された年度が、試験公開年度かを判定します。

    :param year: 判定する年度
    :return: 試験公開年度の場合はTrue、それ以外はFalse
    """
    dt_now = datetime.now()
    now = dt_now.year
    return year > now


####################################################################
# /(年度) にアクセスしたときの処理
####################################################################
@app.route("/")
@cache.cached(query_string=True)
def route_top():
    """
    トップページへのルーティングを処理します。
    今年度または最新年度にリダイレクトします。
    """
    dt_now = datetime.now()
    now = dt_now.year
    latest_year = available_years[-1]

    # 今年度 or 最新年度を表示
    year = now if now in available_years else latest_year

    return redirect(
        url_for(
            "content",
            year=year,
            content="top"
        )
    )


####################################################################
# 世界地図の表示
####################################################################
@app.route('/<int:year>/world_map')
@cache.cached(query_string=True)
def world_map(year: int = None):
    """
    指定された年度の世界地図を表示します。
    年度が指定されていない場合は最新年度を表示します。

    :param year: 表示する年度
    :return: 世界地図のHTMLテンプレート
    """
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
@cache.cached(query_string=True)
def participants(year: int = None):
    """
    指定された年度の出場者一覧を表示します。
    年度が指定されていない場合は最新年度を表示します。

    :param year: 表示する年度
    :return: 出場者一覧のHTMLテンプレート
    """
    # 年度が指定されていない場合は最新年度を表示
    if year not in available_years:
        year = available_years[-1]

    # 引数を取得
    category = request.args.get("category")
    ticket_class = request.args.get("ticket_class")
    cancel = request.args.get("cancel")
    scroll = request.args.get("scroll")
    value = request.args.get("value") or ""

    # 引数が不正な場合はSolo全出場者を表示
    valid_categories = pd.read_csv(
        f'app/static/csv/{year}_participants.csv')["category"].unique().tolist()
    valid_ticket_classes = ["all", "wildcard", "seed_right"]
    valid_cancel = ["show", "hide", "only_cancelled"]

    # まだデータがない年度の場合は、空っぽのページを表示
    if bool(valid_categories) is False:
        return render_template(
            "/common/participants.html",
            participants=[],
            year=year,
            all_category=valid_categories,
            result_url=None,
            is_latest_year=is_latest_year(year),
            available_years=available_years,
            example_questions=example_questions,
            last_updated=last_updated,
            value=value,
            is_early_access=is_early_access(year)
        )

    # 引数が不正な場合はデフォルト値を設定
    if any([
        category not in valid_categories,
        ticket_class not in valid_ticket_classes,
        cancel not in valid_cancel
    ]):
        category = category if category in valid_categories else "Solo"
        ticket_class = ticket_class if ticket_class in valid_ticket_classes else "all"
        cancel = cancel if cancel in valid_cancel else "show"

        # 正しい引数にリダイレクト
        if scroll is not None:
            return redirect(
                url_for(
                    "participants",
                    year=year,
                    category=category,
                    ticket_class=ticket_class,
                    cancel=cancel,
                    scroll=scroll,
                    value=value
                )
            )

        return redirect(
            url_for(
                "participants",
                year=year,
                category=category,
                ticket_class=ticket_class,
                cancel=cancel
            )
        )

    # 参加者リストを取得
    participants_list = get_participants_list(
        year, category, ticket_class, cancel)

    # 結果URLを取得
    try:
        result_url = key.result[year][category]
    except KeyError:
        result_url = None

    return render_template(
        "/common/participants.html",
        participants=participants_list,
        year=year,
        all_category=valid_categories,
        result_url=result_url,
        is_latest_year=is_latest_year(year),
        available_years=available_years,
        example_questions=example_questions,
        last_updated=last_updated,
        value=value,
        is_early_access=is_early_access(year)
    )


####################################################################
# 日本代表
####################################################################
@sitemapper.include(changefreq="yearly", priority=0.8, url_variables={"year": available_years})
@app.route("/<int:year>/japan")
@cache.cached(query_string=True)
def japan(year: int = None):
    """
    指定された年度の日本代表の出場者一覧を表示します。

    :param year: 表示する年度
    :return: 日本代表のHTMLテンプレート
    """
    # 参加者リストを取得
    participants_list = get_participants_list(
        year=year,
        category="all",
        ticket_class="all",
        cancel="show",
        iso_code=392
    )

    return render_template(
        "/common/japan.html",
        participants=participants_list,
        year=year,
        is_latest_year=is_latest_year(year),
        available_years=available_years,
        example_questions=example_questions,
        last_updated=last_updated,
        is_early_access=is_early_access(year)
    )


####################################################################
# 大会結果
####################################################################
# /year/resultはリダイレクト これによりresultページ内ですべての年度の結果を表示可能
@sitemapper.include(changefreq="yearly", priority=0.8, url_variables={"year": available_years})
@app.route("/<int:year>/result")
@cache.cached(query_string=True)
def result(year: int):
    """
    結果ページを表示します。
    年度が指定されていない場合は最新年度を表示します。

    :return: 結果のHTMLテンプレート
    """

    # 結果を取得
    results = get_results(year)

    return render_template(
        "/common/result.html",
        results=results,
        year=year,
        is_latest_year=is_latest_year(year),
        available_years=available_years,
        example_questions=example_questions,
        last_updated=last_updated,
        is_early_access=is_early_access(year)
    )


# 廃止したリンクのリダイレクト
@app.route("/result")
@cache.cached(query_string=True)
def result_redirect():
    """
    すでに廃止したリンクのリダイレクト
    指定された年度の結果ページにリダイレクトします。

    :return: 指定された年度の結果ページへのリダイレクト
    """
    # クエリパラメータを取得
    year = request.args.get("year")

    # 年度が指定されていない場合は最新年度を表示
    if year not in available_years:
        year = available_years[-1]

    return redirect(url_for("result", year=year))


####################################################################
# ルール
####################################################################
@sitemapper.include(changefreq="weekly", priority=0.8, url_variables={"year": available_years})
@app.route("/<int:year>/rule")
@cache.cached(query_string=True)
def rule(year: int = None):
    """
    指定された年度のルールを表示します。
    年度が指定されていない場合は最新年度を表示します。

    :param year: 表示する年度
    :return: ルールのHTMLテンプレート
    """
    # 年度が指定されていない場合は最新年度を表示
    if year not in available_years:
        year = available_years[-1]

    participants_GBB = get_participants_list(  # 昨年度成績上位者
        year=year,
        category="all",
        ticket_class="seed_right",
        cancel="hide",
        GBB=True
    )

    participants_except_GBB = get_participants_list(  # GBB以外のシード権獲得者
        year=year,
        category="all",
        ticket_class="seed_right",
        cancel="hide",
        GBB=False
    )

    cancels = get_participants_list(  # シード権保持者のうち、キャンセルした人
        year=year,
        category="all",
        ticket_class="seed_right",
        cancel="only_cancelled"
    )

    participants_list = [participants_GBB, participants_except_GBB, cancels]

    return render_template(
        f"/{year}/rule.html",
        year=year,
        is_latest_year=is_latest_year(year),
        available_years=available_years,
        participants_list=participants_list,
        example_questions=example_questions,
        last_updated=last_updated,
        is_early_access=is_early_access(year)
    )


####################################################################
# 各年度のページ
####################################################################

combinations = []  # 年度とコンテンツの組み合わせを格納するリスト

# 各年度のページを取得(ルール、world_mapは別関数で扱っているので除外)
for year in available_years:  # 利用可能な年度をループ
    contents = os.listdir(f"./app/templates/{year}")  # 年度に対応するテンプレートファイルを取得
    contents = [content.replace(".html", "") for content in contents]  # 拡張子を除去

    # rule, world_mapは除外
    contents.remove('rule')  # 'rule'をリストから削除
    if 'world_map' in contents:  # 'world_map'が存在する場合
        contents.remove('world_map')  # 'world_map'をリストから削除

    for content in contents:  # 各コンテンツに対して
        combinations.append((year, content))  # 年度とコンテンツの組み合わせを追加

combinations_year = [year for year, _ in combinations]  # 年度のリストを作成
combinations_content = [content for _, content in combinations]  # コンテンツのリストを作成


@sitemapper.include(changefreq="weekly", priority=0.8, url_variables={"year": combinations_year, "content": combinations_content})
@app.route("/<int:year>/<string:content>")
@cache.cached(query_string=True)
def content(year: int = None, content: str = None):
    """
    指定された年度とコンテンツのページを表示します。
    年度が指定されていない場合は最新年度を表示します。

    :param year: 表示する年度
    :param content: 表示するコンテンツ
    :return: コンテンツのHTMLテンプレート
    """
    # 年度が指定されていない場合は最新年度を表示
    if year not in available_years:
        year = available_years[-1]

    # その他のページはそのまま表示
    try:
        return render_template(
            f"/{year}/{content}.html",
            year=year,
            is_latest_year=is_latest_year(year),
            available_years=available_years,
            example_questions=example_questions,
            last_updated=last_updated,
            is_early_access=is_early_access(year)
        )

    # エラーが出たら404を表示
    except jinja2.exceptions.TemplateNotFound:
        return render_template("/common/404.html", example_questions=example_questions), 404


####################################################################
# その他のページ
####################################################################

content_others = os.listdir("./app/templates/others")
content_others = [content.replace(".html", "") for content in content_others]


@sitemapper.include(changefreq="never", priority=0.7, url_variables={"content": content_others})
@app.route("/others/<string:content>")
@cache.cached(query_string=True)
def others(content: str = None):
    """
    その他のページを表示します。

    :param content: 表示するコンテンツ
    :return: その他のコンテンツのHTMLテンプレート
    """
    year = available_years[-1]

    try:
        return render_template(
            f"/others/{content}.html",
            year=year,
            available_years=available_years,
            is_latest_year=is_latest_year(year),
            example_questions=example_questions,
            last_updated=last_updated
        )

    # エラー
    except jinja2.exceptions.TemplateNotFound:
        return render_template("/common/404.html", example_questions=example_questions), 404


####################################################################
# GitHub API (現在は使用していない)
####################################################################

@app.route("/last-commit")
@cache.cached(query_string=True)
def get_last_commit():
    """
    GitHubの最新コミット情報を取得します。

    :return: 最新コミット情報のJSONレスポンス
    """
    headers = {
        'Authorization': f'token {github_token}'
    }
    response = requests.get(
        "https://api.github.com/repos/shumizu418128/gbbinfo2.0/commits", headers=headers)

    if response.status_code == 403:
        return jsonify({"error": "APIのレートリミットに達しました。しばらくしてから再試行してください。"}), 403

    if response.status_code != 200:
        return jsonify({"error": "データの取得に失敗しました"}), 500

    return jsonify(response.json())


# 以下、キャッシュ使用不可

####################################################################
# gemini, discord, Sitemap, robots.txt
####################################################################

# 検索機能
@app.route("/<int:year>/search", methods=["POST"])
def search(year: int = available_years[-1]):
    """
    指定された年度に対して質問を検索します。

    :param year: 検索する年度
    :return: 検索結果のJSONレスポンス
    """
    # 質問を取得
    question = request.json.get("question")

    # geminiで検索
    response_dict = gemini.search(year=year, question=question)

    return jsonify(response_dict)


@app.route("/<int:year>/search_participants", methods=["POST"])
def search_participants_by_keyword(year: int = available_years[-1]):
    """
    指定された年度に対して出場者を検索します。

    :param year: 検索する年度
    :return: 検索結果のJSONレスポンス
    """
    # 出場者を取得
    keyword = request.json.get("keyword")

    # geminiで検索
    response_dict = search_participants(year=year, keyword=keyword)

    return jsonify(response_dict)


@app.route("/.well-known/discord")
def discord():
    """
    Discordの設定ファイルを返します。

    :return: Discord設定ファイル
    """
    return send_file(".well-known/discord")


@app.route("/sitemap.xml")
def sitemap():
    """
    サイトマップを生成して返します。

    :return: サイトマップのXML
    """
    return sitemapper.generate()


@app.route("/robots.txt")
def robots_txt():
    """
    robots.txtファイルを返します。

    :return: robots.txtファイル
    """
    return send_file("robots.txt", mimetype="text/plain")


####################################################################
# favicon.ico
####################################################################

@app.route("/favicon.ico", methods=["GET"])
def favicon_ico():
    """
    favicon.icoファイルを返します。

    :return: favicon.icoファイル
    """
    return send_file("favicon.ico", mimetype="image/vnd.microsoft.icon")


####################################################################
# apple-touch-icon
####################################################################

@app.route("/apple-touch-icon-120x120-precomposed.png", methods=["GET"])
@app.route("/apple-touch-icon-120x120.png", methods=["GET"])
@app.route("/apple-touch-icon-precomposed.png", methods=["GET"])
@app.route("/apple-touch-icon.png", methods=["GET"])
def apple_touch_icon():
    """
    Appleタッチアイコンを返します。

    :return: Appleタッチアイコンの画像
    """
    return send_file("icon_512.png", mimetype="image/png")


####################################################################
# PWS設定
####################################################################

@app.route("/manifest.json")
def manifest():
    """
    PWAのマニフェストファイルを返します。

    :return: マニフェストファイル
    """
    return send_file('manifest.json', mimetype='application/manifest+json')


@app.route("/service-worker.js")
def service_worker():
    """
    サービスワーカーのJavaScriptファイルを返します。

    :return: サービスワーカーのJavaScript
    """
    return send_file('service-worker.js', mimetype='application/javascript')


####################################################################
# エラーハンドラ
####################################################################


@app.errorhandler(404)
def page_not_found(_):
    """
    404エラーページを表示します。

    :return: 404エラーページのHTMLテンプレート
    """
    return render_template("/common/404.html", example_questions=example_questions), 404


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
