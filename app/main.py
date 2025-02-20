import os
import re
import sched
import time
import warnings
from datetime import datetime, timedelta
from threading import Thread

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

from .modules import gemini, spreadsheet
from .modules.config import Config, TestConfig, available_langs, available_years
from .modules.participants import (
    create_world_map,
    get_participants_list,
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

# 本日のおすすめ動画IDを取得
video_id = spreadsheet.get_video_id()
s = sched.scheduler(time.time, time.sleep)


def update_video_id():
    """
    本日のおすすめ動画IDを更新します。

    この関数は、スプレッドシートから最新の動画IDを取得し、
    グローバル変数 video_id を更新します。
    また、更新された video_id をコンソールに出力します。
    """
    global video_id
    video_id = spreadsheet.get_video_id()
    print("video_id を更新しました:", video_id)


def schedule_delay_until_midnight():
    """
    次の日の午前0時までの遅延時間（秒）を計算します。

    現在時刻から次の午前0時までの秒数を計算し、
    スケジューラが次の更新をいつ実行すべきかを決定するために使用されます。

    :return: 次の午前0時までの秒数
    """
    now = datetime.now()
    next_midnight = datetime(now.year, now.month, now.day) + timedelta(days=1)
    delay = (next_midnight - now).total_seconds()
    return delay


def periodic_update():
    """
    定期的に動画IDを更新する関数。

    update_video_id() を呼び出して動画IDを更新し、
    次に schedule_delay_until_midnight() を呼び出して次の午前0時までの遅延時間を取得します。
    その後、s.enter() を使用して、指定された遅延時間の後に periodic_update() 関数自身を再度実行するようにスケジュールします。
    """
    update_video_id()
    delay = schedule_delay_until_midnight()  # 次の0:00までの秒数
    s.enter(delay, 1, periodic_update)


def run_scheduler():
    """
    スケジューラを実行し、定期的な動画IDの更新をスケジュールします。

    最初に schedule_delay_until_midnight() を呼び出して、初回実行までの遅延時間を計算します。
    次に、s.enter() を使用して、periodic_update() 関数をスケジュールします。
    最後に、s.run() を呼び出してスケジューラを開始し、スケジュールされたタスクを実行します。
    """
    # 初回は次の0:00に実行予定
    initial_delay = schedule_delay_until_midnight()
    s.enter(initial_delay, 1, periodic_update)
    s.run()


scheduler_thread = Thread(target=run_scheduler)
scheduler_thread.daemon = (
    True  # メインスレッドが終了したら、このスレッドも終了するように設定
)
scheduler_thread.start()


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
            pd.read_csv(f"app/database/participants/{year}.csv")["category"]
            .unique()
            .tolist()
        )
        valid_categories_dict[year] = valid_categories


@sitemapper.include(
    changefreq="monthly", priority=1.0, url_variables={"year": available_years}
)
@app.route("/<int:year>/participants", methods=["GET"])
@cache.cached(query_string=True)
def participants(year: int):
    """
    指定された年度の出場者一覧を表示します。
    年度が指定されていない場合は最新年度を表示します。

    :param year: 表示する年度
    :return: 出場者一覧のHTMLテンプレート
    """
    # 2022年度の場合はトップページへリダイレクト
    if year == 2022:
        return redirect(url_for("content", year=year, content="top"))

    # 引数を取得
    category = request.args.get("category")
    ticket_class = request.args.get("ticket_class")
    cancel = request.args.get("cancel")
    scroll = request.args.get("scroll")
    value = request.args.get("value")
    if value is None:
        value = ""

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

    return render_template(
        "/common/participants.html",
        participants=participants_list,
        year=year,
        all_category=valid_categories,
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
@cache.cached(query_string=True)
def japan(year: int):
    """
    指定された年度の日本代表の出場者一覧を表示します。

    :param year: 表示する年度
    :return: 日本代表のHTMLテンプレート
    """
    # 2022年度の場合はトップページへリダイレクト
    if year == 2022:
        return redirect(url_for("content", year=year, content="top"))

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
        all_category = os.listdir(f"./app/database/result/{year}")
    except Exception:
        continue  # ファイルが存在しない場合はスキップ

    all_category = [category.replace(".csv", "") for category in all_category]
    all_category_dict[year] = all_category


# /year/resultはリダイレクト これによりresultページ内ですべての年度の結果を表示可能
@sitemapper.include(
    changefreq="yearly", priority=0.8, url_variables={"year": available_years}
)
@app.route("/<int:year>/result")
@cache.cached(query_string=True)
def result(year: int):
    """
    結果ページを表示します。
    年度が指定されていない場合は最新年度を表示します。

    :return: 結果のHTMLテンプレート
    """
    # 引数を取得
    category = request.args.get("category")

    # 2022年度の場合はトップページへリダイレクト
    if year == 2022:
        return redirect(url_for("content", year=year, content="top"))

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
        year = max(available_years)

    return redirect(url_for("result", year=year))


####################################################################
# ルール
####################################################################
@sitemapper.include(
    changefreq="weekly", priority=0.8, url_variables={"year": available_years}
)
@app.route("/<int:year>/rule")
@cache.cached(query_string=True)
def rule(year: int):
    """
    指定された年度のルールを表示します。
    年度が指定されていない場合は最新年度を表示します。

    :param year: 表示する年度
    :return: ルールのHTMLテンプレート
    """
    # 2022年度の場合はトップページへリダイレクト
    if year == 2022:
        return redirect(url_for("content", year=year, content="top"))

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
@cache.cached(query_string=True, timeout=3600)
def content(year: int, content: str):
    """
    指定された年度とコンテンツのページを表示します。
    年度が指定されていない場合は最新年度を表示します。

    :param year: 表示する年度
    :param content: 表示するコンテンツ
    :return: コンテンツのHTMLテンプレート
    """
    # 2022年度の場合はトップページへリダイレクト
    if year == 2022 and content != "top":
        return redirect(url_for("content", year=year, content="top"))

    # その他のページはそのまま表示
    try:
        return render_template(
            f"/{year}/{content}.html",
            year=year,
            is_latest_year=is_latest_year(year),
            available_years=available_years,
            last_updated=last_updated,
            is_early_access=is_early_access(year),
            video_id=video_id,
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
@cache.cached(query_string=True)
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
# 検索, form POST
####################################################################
@app.route("/<int:year>/search", methods=["POST"])
def search(year: int):
    """
    指定された年度に対して質問を検索します。

    :param year: 検索する年度
    :return: 検索結果のJSONレスポンス
    """
    if year == 2022:
        return jsonify({"url": "/2022/top"})

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


def extract_youtube_video_id(url: str) -> str | None:
    """
    YouTubeのURLから動画IDを抽出します。

    :param url: YouTubeのURL
    :return: 動画ID（存在しない場合はNone）
    """
    pattern = r"(?:https?:\/\/)?(?:www\.)?(?:youtube\.com\/(?:watch\?v=|embed\/|v\/|shorts\/)|youtu\.be\/)([a-zA-Z0-9_-]{11})"
    match = re.search(pattern, url)
    return match.group(1) if match else None


@app.route("/post_video", methods=["POST"])
def post_video():
    """
    動画のURLを取得します。

    :return: 動画のURL
    """
    # 動画のURLからIDを取得
    video_url = request.json.get("video_url")
    video_id = extract_youtube_video_id(video_url)

    # スプシに記録
    if video_id is not None:
        Thread(target=spreadsheet.record_video_id, args=(video_id, video_url)).start()

    return jsonify({"status": "ok"}), 200


####################################################################
# discord, Sitemap, robots.txt, ads.txt
####################################################################
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
