import os
import warnings
from datetime import datetime

import jinja2
from flask import (
    Flask,
    abort,
    g,
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
from .modules.config import (
    AVAILABLE_LANGS,
    AVAILABLE_YEARS,
    JAPAN,
    KOREA,
    LANG_NAMES,
    Config,
    TestConfig,
)
from .modules.core.decorators import validate_year
from .modules.core.utils import (
    create_valid_params,
    get_categories_for_year,
    get_current_timestamp,
    get_others_templates,
    get_result_categories_for_year,
    is_early_access,
    is_latest_year,
    is_translated,
    load_template_combinations_optimized,
    validate_params,
)
from .modules.optimization.startup import (
    load_categories_parallel,
    load_result_categories_optimized,
)
from .modules.participants import (
    create_world_map,
    get_participants_list,
    search_participants,
    total_participant_analysis,
    yearly_participant_analysis,
)
from .modules.result import get_result

app = Flask(__name__)
sitemapper = Sitemapper()
sitemapper.init_app(app)

# 特定の警告を無視
warnings.filterwarnings(
    "ignore",
    category=UserWarning,
    message="Flask-Caching: CACHE_TYPE is set to null, caching is effectively disabled.",
)
# テスト環境ではキャッシュを無効化
# ローカル環境にはこの環境変数を設定してある
if os.getenv("ENVIRONMENT_CHECK") == "qawsedrftgyhujikolp":
    print("\n")
    print("******************************************************************")
    print("*                                                                *")
    print("*         GBBINFO-JPN is running in test mode!                   *")
    print("*         Access the application at http://127.0.0.1:8080        *")
    print("*                                                                *")
    print("******************************************************************")
    app.config.from_object(TestConfig)
    cache = Cache(app, config={"CACHE_TYPE": "null"})
    IS_LOCAL = True

# 本番環境ではキャッシュを有効化
# 翻訳は無し
else:
    app.config.from_object(Config)
    cache = Cache(
        app,
        config={
            "CACHE_TYPE": app.config["CACHE_TYPE"],
            "CACHE_DIR": app.config["CACHE_DIR"],
        },
    )
    IS_LOCAL = False

babel = Babel(app)
test = _("test")  # テスト翻訳


####################################################################
# MARK: 定数一覧
####################################################################
# 現在時刻を読み込む(最終更新日時として使用)
DT_NOW, LAST_UPDATED = get_current_timestamp()

# 各年度の全カテゴリを取得（最適化版）
VALID_CATEGORIES_DICT = load_categories_parallel()

# 各年度の全カテゴリを取得（最適化版）
ALL_CATEGORY_DICT = load_result_categories_optimized()

# 各年度のページを取得
COMBINATIONS_YEAR, COMBINATIONS_CONTENT = load_template_combinations_optimized()

# othersテンプレート（最適化版）
CONTENT_OTHERS = get_others_templates()

# プルリクエストかどうか
IS_PULL_REQUEST = os.getenv("IS_PULL_REQUEST") == "true"


####################################################################
# MARK: 共通変数
####################################################################
@app.before_request
def set_request_data():
    """
    リクエストごとに実行される関数。
    URLを取得して、グローバル変数に保存します。
    これにより、リクエストのURLをグローバルにアクセスできるようにします。
    また、セッションに言語が設定されていない場合、デフォルトの言語を設定します。

    Returns:
        None
    """
    g.current_url = request.path

    if "X-Forwarded-For" in request.headers:
        user_ip = request.headers["X-Forwarded-For"].split(",")[0].strip()
        print(f"IPアドレス: {user_ip}", flush=True)

    # 初回アクセス時の言語設定
    if "language" not in session:
        best_match = request.accept_languages.best_match(AVAILABLE_LANGS)
        session["language"] = best_match if best_match else "ja"


@app.context_processor
def inject_variables():
    """
    すべてのページに送る共通変数を設定します。

    Returns:
        dict: 共通変数
    """
    # 年度が公開範囲内か検証
    year_str = g.current_url.split("/")[1]
    is_latest_year_flag = None
    is_early_access_flag = None

    # 年度が最新 or 試験公開年度か検証
    try:
        year = int(year_str)
        if year in AVAILABLE_YEARS:
            is_latest_year_flag = is_latest_year(year)
            is_early_access_flag = is_early_access(year)
    except Exception:
        pass

    return dict(
        available_years=AVAILABLE_YEARS,
        available_langs=AVAILABLE_LANGS,
        lang_names=LANG_NAMES,
        last_updated=LAST_UPDATED,
        current_url=g.current_url,
        language=session.get("language"),
        is_translated=is_translated(g.current_url, session.get("language")),
        is_latest_year=is_latest_year_flag,
        is_early_access=is_early_access_flag,
        is_local=IS_LOCAL,
        is_pull_request=IS_PULL_REQUEST,
    )


@babel.localeselector
def get_locale():
    """
    ユーザーの言語設定を取得します。
    利用可能な言語の中から、セッションに保存された言語を優先的に返します。
    セッションに言語が保存されていない場合は、リクエストの受け入れ言語の中から最適な言語を選択します。

    Returns:
        str: ユーザーの言語設定
    """
    # セッションに言語が設定されているか確認
    if "language" not in session:
        best_match = request.accept_languages.best_match(AVAILABLE_LANGS)
        session["language"] = best_match if best_match else "ja"

    return session["language"]


####################################################################
# MARK: 言語切り替え
####################################################################
@app.route("/lang")
def lang():
    """
    言語を切り替えます。

    Returns:
        Response: リダイレクト先のURL
    """
    # クエリパラメータを取得
    lang = request.args.get("lang")
    referrer = request.args.get("referrer")

    # referrerがない場合はトップページへリダイレクト
    if referrer is None:
        return redirect(url_for("route_top"))

    # langがない場合はセッションに保存された言語を利用
    if lang is None:
        lang = session.get("language")

    # 言語が利用可能な言語であればセッションに保存
    if lang in AVAILABLE_LANGS:
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
# MARK: ルート
####################################################################
@app.route("/")
def route_top():
    """
    トップページへのルーティングを処理します。
    今年度または最新年度にリダイレクトします。

    Returns:
        Response: トップページへのリダイレクト
    """
    dt_now = datetime.now()
    now = dt_now.year
    latest_year = max(AVAILABLE_YEARS)

    # 今年度 or 最新年度を表示
    year = now if now in AVAILABLE_YEARS else latest_year

    return redirect(url_for("content", year=year, content="top"))


####################################################################
# MARK: 世界地図
####################################################################
@app.route("/<int:year>/world_map")
@validate_year
def world_map(year: int):
    # 言語のバリデーション
    user_lang = session.get("language", "ja")
    if user_lang not in AVAILABLE_LANGS:
        user_lang = "ja"

    # マップファイルのパスを作成
    base_path = os.path.join("app", "templates")
    abs_base_path = os.path.abspath(base_path)
    map_filename = f"world_map_{user_lang}.html"
    map_path = os.path.realpath(
        os.path.normpath(os.path.join(base_path, str(year), map_filename))
    )

    # base_path からのパストラバーサル防止
    try:
        # Ensure map_path is strictly within abs_base_path
        if os.path.commonpath([abs_base_path, map_path]) != abs_base_path:
            abort(404)
    except ValueError:
        # Handle invalid paths that could cause os.path.commonpath to fail
        abort(404)

    if not os.path.exists(map_path):
        create_world_map(year=year, user_lang=user_lang)

    return render_template(f"{year}/world_map_{user_lang}.html")


@app.route("/others/all_participants_map")
def all_participants_map():
    """
    全年度の出場者の世界地図を表示します。

    Returns:
        Response: 世界地図のHTMLテンプレート
    """
    # mapを作るために必要な関数
    _ = total_participant_analysis()

    return render_template("others/all_participants_map.html")


####################################################################
# MARK: 出場者一覧
####################################################################
@sitemapper.include(
    changefreq="monthly", priority=1.0, url_variables={"year": AVAILABLE_YEARS}
)
@app.route("/<int:year>/participants", methods=["GET"])
@validate_year
def participants(year: int):
    """
    指定された年度の出場者一覧を表示します。
    年度が指定されていない場合は最新年度を表示します。

    Args:
        year (int): 表示する年度

    Returns:
        Response: 出場者一覧のHTMLテンプレート
    """
    # 2022年度の場合はトップページへリダイレクト
    if year == 2022:
        return redirect(url_for("content", year=year, content="top"))

    # セッションから言語を取得
    user_lang = session.get("language", "ja")

    # 引数を取得
    category = request.args.get("category")
    ticket_class = request.args.get("ticket_class")
    cancel = request.args.get("cancel")
    scroll = request.args.get("scroll")
    value = request.args.get("value")
    if value is None:
        value = ""

    # カテゴリを取得（遅延読み込み対応）
    valid_categories = get_categories_for_year(year, VALID_CATEGORIES_DICT)
    if not valid_categories:
        # データがない年度の場合は、空っぽのページを表示
        return render_template(
            "/common/participants.html",
            participants=[],
            year=year,
            all_category=[],
            result_url=None,
            value=value,
        )

    # 引数の正当性を確認
    are_params_valid = validate_params(
        category=category,
        ticket_class=ticket_class,
        cancel=cancel,
        valid_categories=valid_categories,
    )

    # 引数が不正な場合は修正
    if not are_params_valid:
        # 引数を修正
        category, ticket_class, cancel = create_valid_params(
            category=category,
            ticket_class=ticket_class,
            cancel=cancel,
            valid_categories=valid_categories,
        )

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
    participants_list = get_participants_list(
        year=year,
        category=category,
        ticket_class=ticket_class,
        cancel=cancel,
        user_lang=user_lang,
    )

    return render_template(
        "/common/participants.html",
        participants=participants_list,
        year=year,
        all_category=valid_categories,
        value=value,
    )


####################################################################
# MARK: 日本代表
####################################################################
@sitemapper.include(
    changefreq="yearly", priority=0.8, url_variables={"year": AVAILABLE_YEARS}
)
@app.route("/<int:year>/japan")
@validate_year
def japan(year: int):
    """
    指定された年度の日本代表の出場者一覧を表示します。

    Args:
        year (int): 表示する年度

    Returns:
        Response: 日本代表のHTMLテンプレート
    """
    # 参加者リストを取得
    participants_list = get_participants_list(
        year=year, category="all", ticket_class="all", cancel="show", iso_code=JAPAN
    )

    return render_template(
        "/common/japan.html",
        participants=participants_list,
        year=year,
    )


####################################################################
# MARK: 韓国代表
####################################################################
@sitemapper.include(
    changefreq="yearly", priority=0.8, url_variables={"year": AVAILABLE_YEARS}
)
@app.route("/<int:year>/korea")
@validate_year
def korea(year: int):
    """
    指定された年度の韓国代表の出場者一覧を表示します。

    Args:
        year (int): 表示する年度

    Returns:
        Response: 韓国代表のHTMLテンプレート
    """
    # 参加者リストを取得（韓国のISOコードは410）
    participants_list = get_participants_list(
        year=year, category="all", ticket_class="all", cancel="show", iso_code=KOREA
    )

    return render_template(
        "/common/korea.html",
        participants=participants_list,
        year=year,
    )


####################################################################
# MARK: 大会結果
####################################################################
# /year/resultはリダイレクト これによりresultページ内ですべての年度の結果を表示可能
@sitemapper.include(
    changefreq="yearly", priority=0.8, url_variables={"year": AVAILABLE_YEARS}
)
@app.route("/<int:year>/result")
@validate_year
def result(year: int):
    """
    結果ページを表示します。
    年度が指定されていない場合は最新年度を表示します。

    Args:
        year (int): 表示する年度

    Returns:
        Response: 結果のHTMLテンプレート
    """
    # 引数を取得
    category = request.args.get("category")

    # カテゴリを取得（遅延読み込み対応）
    all_category = get_result_categories_for_year(year, ALL_CATEGORY_DICT)
    if not all_category:
        return render_template(
            "/common/result.html",
            year=year,
        )

    # 引数が正しいか確認
    # カテゴリが不正な場合はLoopstationへリダイレクト
    if category not in all_category:
        category = "Loopstation"
        return redirect(url_for("result", year=year, category=category))

    # 結果を取得
    format, result = get_result(category=category, year=year)

    return render_template(
        "/common/result.html",
        year=year,
        result=result,
        all_category=all_category,
        category=category,
        format=format,
    )


# 廃止したリンクのリダイレクト
@app.route("/result")
def result_redirect():
    """
    すでに廃止したリンクのリダイレクト。
    指定された年度の結果ページにリダイレクトします。

    Returns:
        Response: 指定された年度の結果ページへのリダイレクト
    """
    # クエリパラメータを取得
    year = request.args.get("year")

    # 年度が指定されていない場合は最新年度を表示
    if year not in AVAILABLE_YEARS:
        year = max(AVAILABLE_YEARS)

    return redirect(url_for("result", year=year))


####################################################################
# MARK: ルール
####################################################################
@sitemapper.include(
    changefreq="weekly", priority=0.8, url_variables={"year": AVAILABLE_YEARS}
)
@app.route("/<int:year>/rule")
@validate_year
def rule(year: int):
    """
    指定された年度のルールを表示します。
    年度が指定されていない場合は最新年度を表示します。

    Args:
        year (int): 表示する年度

    Returns:
        Response: ルールのHTMLテンプレート
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
        participants_list=participants_list,
    )


####################################################################
# MARK: 各年度のページ
####################################################################
@sitemapper.include(
    changefreq="weekly",
    priority=0.8,
    url_variables={"year": COMBINATIONS_YEAR, "content": COMBINATIONS_CONTENT},
)
@app.route("/<int:year>/<string:content>")
@validate_year
def content(year: int, content: str):
    """
    指定された年度とコンテンツのページを表示します。
    年度が指定されていない場合は最新年度を表示します。

    Args:
        year (int): 表示する年度
        content (str): 表示するコンテンツ

    Returns:
        Response: コンテンツのHTMLテンプレート
    """
    # その他のページはそのまま表示
    try:
        return render_template(
            f"/{year}/{content}.html",
            year=year,
        )

    # エラーが出たら404を表示
    except jinja2.exceptions.TemplateNotFound:
        return render_template("/common/404.html"), 404


####################################################################
# MARK: othersページ
####################################################################
@sitemapper.include(
    changefreq="never", priority=0.7, url_variables={"content": CONTENT_OTHERS}
)
@app.route("/others/<string:content>")
def others(content: str):
    """
    その他のページを表示します。

    Args:
        content (str): 表示するコンテンツ

    Returns:
        Response: その他のコンテンツのHTMLテンプレート
    """
    # 年度は最新に設定
    year = max(AVAILABLE_YEARS)

    try:
        return render_template(
            f"/others/{content}.html",
            year=year,
        )

    # エラー
    except jinja2.exceptions.TemplateNotFound:
        return render_template("/common/404.html"), 404


# 以下API


####################################################################
# MARK: 検索機能
####################################################################
@app.route("/<int:year>/search", methods=["POST"])
def search(year: int):
    """
    指定された年度に対して質問を検索します。

    Args:
        year (int): 検索する年度

    Returns:
        Response: 検索結果のJSONレスポンス
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

    print(response_dict)

    return jsonify(response_dict)


@app.route("/<int:year>/search_participants", methods=["POST"])
def search_participants_by_keyword(year: int):
    """
    指定された年度に対して出場者を検索します。

    Args:
        year (int): 検索する年度

    Returns:
        Response: 検索結果のJSONレスポンス
    """
    # 出場者を取得
    keyword = request.json.get("keyword")

    # geminiで検索
    response_dict = search_participants(year=year, keyword=keyword)

    return jsonify(response_dict)


@app.route("/search_suggestions", methods=["POST"])
def search_suggestions():
    """
    入力に基づいて検索候補を返します。

    Returns:
        Response: 検索候補のJSONレスポンス
    """
    input = request.json.get("input")
    suggestions = gemini.search_suggestions(input)
    return jsonify({"suggestions": suggestions})


####################################################################
# MARK: データで見るGBB (API)
####################################################################
@app.route("/analyze_data/<int:year>")
def analyze_data_yearly(year: int):
    """
    データで見るGBBのページを表示します。

    Args:
        year (int): 表示する年度

    Returns:
        Response: データで見るGBBのHTMLテンプレート
    """
    user_lang = session.get("language", "ja")  # セッションから言語を取得
    yearly_analysis = yearly_participant_analysis(year=year, user_lang=user_lang)

    return jsonify(yearly_analysis)


@app.route("/analyze_data/total")
@cache.cached()
def analyze_data_total():
    """
    データで見るGBBのページを表示します。

    Returns:
        Response: データで見るGBBのHTMLテンプレート
    """
    total_analysis = total_participant_analysis()

    return jsonify(total_analysis)


####################################################################
# MARK: Sitemap, 認証系
####################################################################
@app.route("/.well-known/discord")
def discord():
    """
    Discordの設定ファイルを返します。

    Returns:
        Response: Discord設定ファイル
    """
    return send_file(".well-known/discord")


@app.route("/sitemap.xml")
@cache.cached()
def sitemap():
    """
    サイトマップを生成して返します。

    Returns:
        Response: サイトマップのXML
    """
    return sitemapper.generate()


@app.route("/robots.txt")
def robots_txt():
    """
    robots.txtファイルを返します。

    Returns:
        Response: robots.txtファイル
    """
    return send_file("robots.txt", mimetype="text/plain")


@app.route("/ads.txt")
def ads_txt():
    """
    ads.txtファイルを返します。

    Returns:
        Response: ads.txtファイル
    """
    return send_file("ads.txt", mimetype="text/plain")


@app.route("/naverc158f3394cb78ff00c17f0a687073317.html")
def naver_verification():
    """
    NAVERの認証ファイルを返します。

    Returns:
        Response: NAVERの認証ファイル
    """
    return send_file("naverc158f3394cb78ff00c17f0a687073317.html")


####################################################################
# MARK: favicon.ico
####################################################################
@app.route("/favicon.ico", methods=["GET"])
def favicon_ico():
    """
    favicon.icoファイルを返します。

    Returns:
        Response: favicon.icoファイル
    """
    return send_file("favicon.ico", mimetype="image/vnd.microsoft.icon")


####################################################################
# MARK: apple-touch-icon
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

    Returns:
        Response: Appleタッチアイコンの画像
    """
    return send_file("icon_512.png", mimetype="image/png")


####################################################################
# MARK: PWS設定
####################################################################
@app.route("/manifest.json")
def manifest():
    """
    PWAのマニフェストファイルを返します。

    Returns:
        Response: マニフェストファイル
    """
    return send_file("manifest.json", mimetype="application/manifest+json")


@app.route("/service-worker.js")
def service_worker():
    """
    サービスワーカーのJavaScriptファイルを返します。

    Returns:
        Response: サービスワーカーのJavaScript
    """
    return send_file("service-worker.js", mimetype="application/javascript")


####################################################################
# MARK: エラーハンドラ
####################################################################
@app.errorhandler(404)
def page_not_found(_):
    """
    404エラーページを表示します。

    Args:
        _ (Exception): 例外オブジェクト（未使用）

    Returns:
        tuple: 404エラーページのHTMLテンプレートとステータスコード
    """
    return render_template("/common/404.html"), 404
