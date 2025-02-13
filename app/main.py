import os
import warnings
from datetime import datetime

import jinja2
import pandas as pd
from flask import (
    Flask,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    session,
    url_for,
)
from flask_babel import Babel, _
from flask_caching import Cache
from flask_sitemapper import Sitemapper

from .modules import gemini
from .modules.config import Config, TestConfig, available_langs, available_years
from .modules.participants import (
    create_world_map,
    get_participants_list,
    instagram,
    search_participants,
)
from .modules.result import get_result
from .modules.translate import translate

app = Flask(__name__)
sitemapper = Sitemapper()
sitemapper.init_app(app)

# 現在時刻を読み込む(最終更新日時として使用)
dt_now = datetime.now()
last_updated = "UPDATE " + dt_now.strftime("%Y/%m/%d %H:%M:%S")

# 特定の警告を無視
warnings.filterwarnings(
    "ignore",
    category=UserWarning,
    message="Flask-Caching: CACHE_TYPE is set to null, caching is effectively disabled.",
)
# テスト環境ではキャッシュを無効化
# ローカル環境にはこの環境変数を設定してある
if os.getenv("ENVIRONMENT_CHECK") == "qawsedrftgyhujikolp":
    print("\nくぁwせdrftgyふじこlp\n")
    app.config.from_object(TestConfig)
    cache = Cache(app, config={"CACHE_TYPE": "null"})

# 本番環境ではキャッシュを有効化
else:
    translate()
    app.config.from_object(Config)
    cache = Cache(
        app,
        config={
            "CACHE_TYPE": app.config["CACHE_TYPE"],
            "CACHE_DIR": app.config["CACHE_DIR"],
        },
    )

babel = Babel(app)
test = _("test")  # テスト翻訳


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
    return year == max(available_years) or year == now


def is_early_access(year):
    """
    指定された年度が、試験公開年度かを判定します。

    :param year: 判定する年度
    :return: 試験公開年度の場合はTrue、それ以外はFalse
    """
    dt_now = datetime.now()
    now = dt_now.year
    return year > now


@babel.localeselector
def get_locale():
    """
    この関数は、ユーザーの言語設定を取得します。
    利用可能な言語の中から、セッションに保存された言語を優先的に返します。
    セッションに言語が保存されていない場合は、リクエストの受け入れ言語の中から最適な言語を選択します。

    :return: ユーザーの言語設定
    """
    user_lang = session.get("language")
    return (
        user_lang
        if user_lang in available_langs
        else request.accept_languages.best_match(available_langs)
    )


####################################################################
# 言語切り替え
####################################################################
@app.route("/lang")
def lang():
    """
    言語を切り替えます。

    :return: リダイレクト先のURL
    """
    # クエリパラメータを取得
    lang = request.args.get("lang")
    referrer = request.args.get("referrer")

    # 言語が利用可能な言語であればセッションに保存
    if lang in available_langs:
        session["language"] = lang
    else:
        session["language"] = "ja"

    # リダイレクト先を分析
    non_content_func = ["participants", "japan", "result", "rule"]
    year = referrer.split("/")[1]
    content_name = referrer.split("/")[2]

    # リダイレクト先を決定
    # others
    if year == "others":
        return redirect(url_for("others", content=content_name))

    # content関数以外
    if content_name in non_content_func:
        return redirect(url_for(content_name, year=year))

    # content関数
    return redirect(url_for("content", year=year, content=content_name))


####################################################################
# /(年度) にアクセスしたときの処理
####################################################################
@app.route("/")
def route_top():
    """
    トップページへのルーティングを処理します。
    今年度または最新年度にリダイレクトします。
    """
    dt_now = datetime.now()
    now = dt_now.year
    latest_year = max(available_years)

    # 今年度 or 最新年度を表示
    year = now if now in available_years else latest_year

    return redirect(url_for("content", year=year, content="top"))


####################################################################
# 世界地図の表示
####################################################################
@app.route("/<int:year>/world_map")
@cache.cached(query_string=True)
def world_map(year: int):
    """
    指定された年度の世界地図を表示します。
    年度が指定されていない場合は最新年度を表示します。

    :param year: 表示する年度
    :return: 世界地図のHTMLテンプレート
    """

    # 世界地図作成
    create_world_map(year)

    return render_template(f"{year}/world_map.html")


####################################################################
# 出場者一覧
####################################################################

# 各年度の全カテゴリを取得
valid_categories_dict = {}
for year in available_years:
    if year != 2022:
        valid_categories = (
            pd.read_csv(f"app/static/csv/participants/{year}.csv")["category"]
            .unique()
            .tolist()
        )
        valid_categories_dict[year] = valid_categories


@sitemapper.include(
    changefreq="monthly", priority=1.0, url_variables={"year": available_years}
)
@app.route("/<int:year>/participants", methods=["GET"])
def participants(year: int):
    """
    指定された年度の出場者一覧を表示します。
    年度が指定されていない場合は最新年度を表示します。

    :param year: 表示する年度
    :return: 出場者一覧のHTMLテンプレート
    """
    # 年度が指定されていない場合は最新年度を表示
    if year not in available_years:
        year = max(available_years)

    # 引数を取得
    category = request.args.get("category")
    ticket_class = request.args.get("ticket_class")
    cancel = request.args.get("cancel")
    scroll = request.args.get("scroll")
    value = request.args.get("value") or ""

    # カテゴリを取得
    try:
        valid_categories = valid_categories_dict[year]
    except KeyError:
        # そもそもデータがない年度の場合は、空っぽのページを表示
        return render_template(
            "/common/participants.html",
            participants=[],
            year=year,
            all_category=[],
            result_url=None,
            is_latest_year=is_latest_year(year),
            available_years=available_years,
            last_updated=last_updated,
            value=value,
            is_early_access=is_early_access(year),
        )
    valid_ticket_classes = ["all", "wildcard", "seed_right"]
    valid_cancel = ["show", "hide", "only_cancelled"]

    # 引数の正当性を確認
    args_valid = all(
        [
            category in valid_categories,
            ticket_class in valid_ticket_classes,
            cancel in valid_cancel,
        ]
    )

    # 引数が不正な場合はデフォルト値を設定
    if not args_valid:
        category = category if category in valid_categories else "Solo"
        ticket_class = ticket_class if ticket_class in valid_ticket_classes else "all"
        cancel = cancel if cancel in valid_cancel else "show"

        # スクロール引数がある場合、引数の情報を保持してリダイレクト
        if scroll is not None:
            return redirect(
                url_for(
                    "participants",
                    year=year,
                    category=category,
                    ticket_class=ticket_class,
                    cancel=cancel,
                    scroll=scroll,
                    value=value,
                )
            )

        # スクロール引数がない場合のリダイレクト
        return redirect(
            url_for(
                "participants",
                year=year,
                category=category,
                ticket_class=ticket_class,
                cancel=cancel,
            )
        )

    # 参加者リストを取得
    participants_list = get_participants_list(year, category, ticket_class, cancel)

    # 結果URLを取得
    try:
        result_url = instagram[year][category]
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
        last_updated=last_updated,
        value=value,
        is_early_access=is_early_access(year),
    )


####################################################################
# 日本代表
####################################################################
@sitemapper.include(
    changefreq="yearly", priority=0.8, url_variables={"year": available_years}
)
@app.route("/<int:year>/japan")
def japan(year: int):
    """
    指定された年度の日本代表の出場者一覧を表示します。

    :param year: 表示する年度
    :return: 日本代表のHTMLテンプレート
    """
    # 参加者リストを取得
    participants_list = get_participants_list(
        year=year, category="all", ticket_class="all", cancel="show", iso_code=392
    )

    return render_template(
        "/common/japan.html",
        participants=participants_list,
        year=year,
        is_latest_year=is_latest_year(year),
        available_years=available_years,
        last_updated=last_updated,
        is_early_access=is_early_access(year),
    )


####################################################################
# 大会結果
####################################################################

# 各年度の全カテゴリを取得
all_category_dict = {}
for year in available_years:
    # フォルダの中にあるCSVファイル一覧を取得
    try:
        all_category = os.listdir(f"./app/static/csv/result/{year}")
    except Exception:
        continue  # ファイルが存在しない場合はスキップ

    all_category = [category.replace(".csv", "") for category in all_category]
    all_category_dict[year] = all_category


# /year/resultはリダイレクト これによりresultページ内ですべての年度の結果を表示可能
@sitemapper.include(
    changefreq="yearly", priority=0.8, url_variables={"year": available_years}
)
@app.route("/<int:year>/result")
def result(year: int):
    """
    結果ページを表示します。
    年度が指定されていない場合は最新年度を表示します。

    :return: 結果のHTMLテンプレート
    """
    # 引数を取得
    category = request.args.get("category")

    # カテゴリを取得
    try:
        all_category = all_category_dict[year]
    except KeyError:
        return render_template(
            "/common/result.html",
            year=year,
            is_latest_year=is_latest_year(year),
            available_years=available_years,
            last_updated=last_updated,
            is_early_access=is_early_access(year),
        )

    # 引数が正しいか確認
    # カテゴリが不正な場合はSoloへリダイレクト
    if category not in all_category:
        category = "Solo"
        return redirect(url_for("result", year=year, category=category))

    # 結果を取得
    format, result = get_result(category=category, year=year)

    return render_template(
        "/common/result.html",
        year=year,
        is_latest_year=is_latest_year(year),
        available_years=available_years,
        last_updated=last_updated,
        is_early_access=is_early_access(year),
        result=result,
        all_category=all_category,
        category=category,
        format=format,
    )


# 廃止したリンクのリダイレクト
@app.route("/result")
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
        year = max(available_years)

    return redirect(url_for("result", year=year))


####################################################################
# ルール
####################################################################
@sitemapper.include(
    changefreq="weekly", priority=0.8, url_variables={"year": available_years}
)
@app.route("/<int:year>/rule")
def rule(year: int):
    """
    指定された年度のルールを表示します。
    年度が指定されていない場合は最新年度を表示します。

    :param year: 表示する年度
    :return: ルールのHTMLテンプレート
    """

    participants_GBB = get_participants_list(  # 昨年度成績上位者
        year=year, category="all", ticket_class="seed_right", cancel="hide", GBB=True
    )

    participants_except_GBB = get_participants_list(  # GBB以外のシード権獲得者
        year=year, category="all", ticket_class="seed_right", cancel="hide", GBB=False
    )

    cancels = get_participants_list(  # シード権保持者のうち、キャンセルした人
        year=year, category="all", ticket_class="seed_right", cancel="only_cancelled"
    )

    participants_list = [participants_GBB, participants_except_GBB, cancels]

    return render_template(
        f"/{year}/rule.html",
        year=year,
        is_latest_year=is_latest_year(year),
        available_years=available_years,
        participants_list=participants_list,
        last_updated=last_updated,
        is_early_access=is_early_access(year),
    )


####################################################################
# 各年度のページ
####################################################################

combinations = []  # 年度とコンテンツの組み合わせを格納するリスト

# 各年度のページを取得(ルール、world_mapは別関数で扱っているので除外)
for year in available_years:  # 利用可能な年度をループ
    contents = os.listdir(
        f"./app/templates/{year}"
    )  # 年度に対応するテンプレートファイルを取得
    contents = [content.replace(".html", "") for content in contents]  # 拡張子を除去

    # rule, world_mapは除外
    if "rule" in contents:
        contents.remove("rule")
    if "world_map" in contents:
        contents.remove("world_map")

    for content in contents:  # 各コンテンツに対して
        combinations.append((year, content))  # 年度とコンテンツの組み合わせを追加

combinations_year = [year for year, _ in combinations]  # 年度のリストを作成
combinations_content = [
    content for _, content in combinations
]  # コンテンツのリストを作成


@sitemapper.include(
    changefreq="weekly",
    priority=0.8,
    url_variables={"year": combinations_year, "content": combinations_content},
)
@app.route("/<int:year>/<string:content>")
def content(year: int, content: str):
    """
    指定された年度とコンテンツのページを表示します。
    年度が指定されていない場合は最新年度を表示します。

    :param year: 表示する年度
    :param content: 表示するコンテンツ
    :return: コンテンツのHTMLテンプレート
    """

    # その他のページはそのまま表示
    try:
        return render_template(
            f"/{year}/{content}.html",
            year=year,
            is_latest_year=is_latest_year(year),
            available_years=available_years,
            last_updated=last_updated,
            is_early_access=is_early_access(year),
        )

    # エラーが出たら404を表示
    except jinja2.exceptions.TemplateNotFound:
        return render_template("/common/404.html"), 404


####################################################################
# その他のページ
####################################################################

content_others = os.listdir("./app/templates/others")
content_others = [content.replace(".html", "") for content in content_others]


@sitemapper.include(
    changefreq="never", priority=0.7, url_variables={"content": content_others}
)
@app.route("/others/<string:content>")
def others(content: str):
    """
    その他のページを表示します。

    :param content: 表示するコンテンツ
    :return: その他のコンテンツのHTMLテンプレート
    """
    # 年度は最新に設定
    year = max(available_years)

    try:
        return render_template(
            f"/others/{content}.html",
            year=year,
            available_years=available_years,
            is_latest_year=is_latest_year(year),
            last_updated=last_updated,
        )

    # エラー
    except jinja2.exceptions.TemplateNotFound:
        return render_template("/common/404.html"), 404


# 以下、キャッシュ使用不可

####################################################################
# gemini, discord, Sitemap, robots.txt
####################################################################


# 検索機能
@app.route("/<int:year>/search", methods=["POST"])
def search(year: int):
    """
    指定された年度に対して質問を検索します。

    :param year: 検索する年度
    :return: 検索結果のJSONレスポンス
    """
    # 質問を取得
    question = request.json.get("question")

    # キャッシュ検索
    response_dict = gemini.search_cache(year=year, question=question)

    # キャッシュがない場合はgeminiで検索
    if response_dict is None:
        response_dict = gemini.search(year=year, question=question)

    return jsonify(response_dict)


@app.route("/<int:year>/search_participants", methods=["POST"])
def search_participants_by_keyword(year: int):
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


@app.route("/search_suggestions", methods=["POST"])
def search_suggestions():
    input = request.json.get("input")
    suggestions = gemini.search_suggestions(input)
    return jsonify({"suggestions": suggestions})


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


@app.route("/ads.txt")
def ads_txt():
    """
    ads.txtファイルを返します。

    :return: ads.txtファイル
    """
    return send_file("ads.txt", mimetype="text/plain")


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


@app.route("/apple-touch-icon-152x152-precomposed.png", methods=["GET"])
@app.route("/apple-touch-icon-152x152.png", methods=["GET"])
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
    return send_file("manifest.json", mimetype="application/manifest+json")


@app.route("/service-worker.js")
def service_worker():
    """
    サービスワーカーのJavaScriptファイルを返します。

    :return: サービスワーカーのJavaScript
    """
    return send_file("service-worker.js", mimetype="application/javascript")


####################################################################
# エラーハンドラ
####################################################################


@app.errorhandler(404)
def page_not_found(_):
    """
    404エラーページを表示します。

    :return: 404エラーページのHTMLテンプレート
    """
    return render_template("/common/404.html"), 404
