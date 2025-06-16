import os
import warnings
from datetime import datetime
from functools import lru_cache

import jinja2
import pandas as pd
from flask import (
    Flask,
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
    LANG_NAMES,
    Config,
    TestConfig,
)
from .modules.participants import (
    create_world_map,
    get_participants_list,
    search_participants,
    total_participant_analysis,
    yearly_participant_analysis,
)
from .modules.persistent_cache import persistent_cache
from .modules.result import get_result
from .modules.translate import start_background_translation

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

# 本番環境ではキャッシュを有効化
# 多言語対応のため実際にはworld_mapのみキャッシュを有効化
else:
    # 軽量な翻訳処理（起動速度重視）
    print("アプリケーション起動中...", flush=True)

    # 常にバックグラウンドで翻訳処理を実行（起動をブロックしない）
    print("バックグラウンドで翻訳処理を開始します...", flush=True)
    translation_thread = start_background_translation()

    print("アプリケーションを開始します", flush=True)

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


####################################################################
# MARK: 定数一覧
####################################################################
# ISO 3166-1 numeric
JAPAN = 392
KOREA = 410


# 現在時刻を読み込む(最終更新日時として使用)
DT_NOW = datetime.now()
LAST_UPDATED = "UPDATE " + DT_NOW.strftime("%Y/%m/%d %H:%M:%S") + " JST"


# 最適化されたCSVデータ読み込み（永続的キャッシュ使用）
def load_csv_optimized(year: int) -> pd.DataFrame:
    """
    指定された年度のCSVファイルを永続的キャッシュ機能付きで読み込みます。

    Args:
        year (int): 読み込む年度

    Returns:
        pd.DataFrame: CSVデータのDataFrame。ファイルが存在しない場合は空のDataFrameを返します。
    """
    return persistent_cache.get_csv_data(year)


def load_categories_parallel():
    """
    カテゴリデータを最小限で読み込みます（起動速度重視）。
    最新2年度のデータのみを起動時に読み込み、他の年度は遅延読み込みで対応します。

    Returns:
        dict: 年度をキーとし、カテゴリリストを値とする辞書
    """
    categories_dict = {}

    # 最新2年度のみを起動時に読み込み
    priority_years = sorted(AVAILABLE_YEARS, reverse=True)[:2]

    for year in priority_years:
        categories_dict[year] = persistent_cache.get_categories(year)

    return categories_dict


# 各年度の全カテゴリを取得（最適化版）
VALID_CATEGORIES_DICT = load_categories_parallel()


def load_result_categories_optimized():
    """
    結果カテゴリを最小限で読み込みます（起動速度重視）。
    最新2年度のデータのみを起動時に読み込み、他の年度は遅延読み込みで対応します。

    Returns:
        dict: 年度をキーとし、結果カテゴリリストを値とする辞書
    """
    categories_dict = {}
    # 最新2年度のみを起動時に読み込み
    priority_years = sorted(AVAILABLE_YEARS, reverse=True)[:2]

    for year in priority_years:
        categories_dict[year] = persistent_cache.get_result_categories(year)

    return categories_dict


# 各年度の全カテゴリを取得（最適化版）
ALL_CATEGORY_DICT = load_result_categories_optimized()


@lru_cache(maxsize=32)
def get_template_contents(year: int) -> list:
    """
    指定された年度のテンプレートコンテンツ一覧をキャッシュ機能付きで取得します。
    rule, world_mapテンプレートは除外されます。

    Args:
        year (int): 取得する年度

    Returns:
        list: テンプレートファイル名のリスト（拡張子なし）。
              ディレクトリが存在しない場合は空のリストを返します。
    """
    try:
        templates_dir_path = os.path.join(".", "app", "templates", str(year))
        contents = os.listdir(templates_dir_path)
        contents = [content.replace(".html", "") for content in contents]

        # rule, world_mapは除外
        contents = [c for c in contents if c not in ["rule", "world_map"]]
        return contents
    except OSError:
        return []


@lru_cache(maxsize=1)
def get_others_templates() -> list:
    """
    othersディレクトリのテンプレート一覧をキャッシュ機能付きで取得します。

    Returns:
        list: othersテンプレートファイル名のリスト（拡張子なし）。
              ディレクトリが存在しない場合は空のリストを返します。
    """
    try:
        others_templates_path = os.path.join(".", "app", "templates", "others")
        contents = os.listdir(others_templates_path)
        return [content.replace(".html", "") for content in contents]
    except OSError:
        return []


def load_template_combinations_optimized():
    """
    テンプレート組み合わせを最適化して読み込みます（起動速度重視）。
    最新2年度のテンプレートのみを起動時に読み込み、他の年度は遅延読み込みで対応します。

    Returns:
        list: (年度, コンテンツ名) のタプルのリスト
    """
    combinations = []
    # 最新2年度のみを優先読み込み
    priority_years = sorted(AVAILABLE_YEARS, reverse=True)[:2]

    for year in priority_years:
        contents = get_template_contents(year)
        for content in contents:
            combinations.append((year, content))

    return combinations


# 各年度のページを取得（最適化版）
combinations = load_template_combinations_optimized()
COMBINATIONS_YEAR = [year for year, _ in combinations]
COMBINATIONS_CONTENT = [content for _, content in combinations]

# othersテンプレート（最適化版）
CONTENT_OTHERS = get_others_templates()


# 翻訳が存在するページのパスを取得（永続的キャッシュ使用）
def get_translated_template_paths():
    """
    翻訳されたテンプレートパスを永続的キャッシュから取得します。
    POファイルを解析して翻訳が存在するページのパス一覧を返します。

    Returns:
        set: 翻訳されたページのパスセット。
             POファイルが存在しない場合は空のセットを返します。
    """
    return persistent_cache.get_translated_paths()


# 起動時は空のセットで初期化（必要時に遅延読み込み）
TRANSLATED_TEMPLATE_PATHS = set()


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


def is_translated(url, target_lang=None):
    """
    POファイルを読み込んで、指定されたページに翻訳が提供されているかをチェックします。

    Args:
        url (str): ページのURL
        target_lang (str): 対象言語（Noneの場合は現在のセッション言語）

    Returns:
        bool: 翻訳が提供されている場合True、されていない場合False
    """
    # 日本語の場合は常にTrue（元言語）
    if target_lang == "ja":
        return True

    # 遅延読み込みで翻訳パスを取得
    translated_paths = get_translated_template_paths()
    return url in translated_paths


@app.context_processor
def inject_variables():
    """
    すべてのページに送る共通変数を設定します。

    Returns:
        dict: 共通変数
    """
    return dict(
        available_years=AVAILABLE_YEARS,
        available_langs=AVAILABLE_LANGS,
        lang_names=LANG_NAMES,
        last_updated=LAST_UPDATED,
        current_url=g.current_url,
        language=session.get("language"),
        is_translated=is_translated(g.current_url, session.get("language")),
    )


####################################################################
# MARK: ヘルパー関数
####################################################################
# 最新年度かを判定
# 今年 or 最新年度のみTrue
def is_latest_year(year):
    """
    指定された年度が最新年度または今年であるかを判定します。

    Args:
        year (int): 判定する年度

    Returns:
        bool: 最新年度または今年の場合はTrue、それ以外はFalse
    """
    dt_now = datetime.now()
    now = dt_now.year
    return year == max(AVAILABLE_YEARS) or year == now


def is_early_access(year):
    """
    指定された年度が、試験公開年度かを判定します。

    Args:
        year (int): 判定する年度

    Returns:
        bool: 試験公開年度の場合はTrue、それ以外はFalse
    """
    dt_now = datetime.now()
    now = dt_now.year
    return year > now


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
def world_map(year: int):
    # 年度・言語のバリデーション
    if year not in AVAILABLE_YEARS:
        return render_template("/common/404.html"), 404
    user_lang = session.get("language", "ja")
    if user_lang not in AVAILABLE_LANGS:
        user_lang = "ja"

    base_path = os.path.join("app", "templates")
    abs_base_path = os.path.abspath(base_path)
    map_filename = f"world_map_{user_lang}.html"
    map_path = os.path.abspath(os.path.join(base_path, str(year), map_filename))

    # base_path からのパストラバーサル防止
    if not map_path.startswith(abs_base_path):
        return render_template("/common/404.html"), 404

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
def participants(year: int):
    """
    指定された年度の出場者一覧を表示します。
    年度が指定されていない場合は最新年度を表示します。

    Args:
        year (int): 表示する年度

    Returns:
        Response: 出場者一覧のHTMLテンプレート
    """
    # 年度が許容範囲内か検証
    if year not in AVAILABLE_YEARS or not isinstance(year, int):
        return render_template("error.html", message="Invalid year specified.")

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
    def get_categories_for_year(year):
        if year in VALID_CATEGORIES_DICT:
            return VALID_CATEGORIES_DICT[year]

        # 遅延読み込み：永続的キャッシュから取得
        categories = persistent_cache.get_categories(year)
        VALID_CATEGORIES_DICT[year] = categories  # メモリキャッシュに保存
        return categories

    valid_categories = get_categories_for_year(year)
    if not valid_categories:
        # データがない年度の場合は、空っぽのページを表示
        return render_template(
            "/common/participants.html",
            participants=[],
            year=year,
            all_category=[],
            result_url=None,
            is_latest_year=is_latest_year(year),
            value=value,
            is_early_access=is_early_access(year),
        )
    valid_ticket_classes = ["all", "wildcard", "seed_right"]
    valid_cancel = ["show", "hide", "only_cancelled"]

    # 引数の正当性を確認
    category_is_valid = category in valid_categories
    ticket_class_is_valid = ticket_class in valid_ticket_classes
    cancel_is_valid = cancel in valid_cancel
    args_valid = all([category_is_valid, ticket_class_is_valid, cancel_is_valid])

    # 引数が不正な場合はデフォルト値を設定
    if not args_valid:
        category = category if category in valid_categories else "Loopstation"
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
        is_latest_year=is_latest_year(year),
        value=value,
        is_early_access=is_early_access(year),
    )


####################################################################
# MARK: 日本代表
####################################################################
@sitemapper.include(
    changefreq="yearly", priority=0.8, url_variables={"year": AVAILABLE_YEARS}
)
@app.route("/<int:year>/japan")
def japan(year: int):
    """
    指定された年度の日本代表の出場者一覧を表示します。

    Args:
        year (int): 表示する年度

    Returns:
        Response: 日本代表のHTMLテンプレート
    """
    # 2022年度の場合はトップページへリダイレクト
    if year == 2022:
        return redirect(url_for("content", year=year, content="top"))

    # 参加者リストを取得
    participants_list = get_participants_list(
        year=year, category="all", ticket_class="all", cancel="show", iso_code=JAPAN
    )

    return render_template(
        "/common/japan.html",
        participants=participants_list,
        year=year,
        is_latest_year=is_latest_year(year),
        is_early_access=is_early_access(year),
    )


####################################################################
# MARK: 韓国代表
####################################################################
@sitemapper.include(
    changefreq="yearly", priority=0.8, url_variables={"year": AVAILABLE_YEARS}
)
@app.route("/<int:year>/korea")
def korea(year: int):
    """
    指定された年度の韓国代表の出場者一覧を表示します。

    Args:
        year (int): 表示する年度

    Returns:
        Response: 韓国代表のHTMLテンプレート
    """
    # 2022年度の場合はトップページへリダイレクト
    if year == 2022:
        return redirect(url_for("content", year=year, content="top"))

    # 参加者リストを取得（韓国のISOコードは410）
    participants_list = get_participants_list(
        year=year, category="all", ticket_class="all", cancel="show", iso_code=KOREA
    )

    return render_template(
        "/common/korea.html",
        participants=participants_list,
        year=year,
        is_latest_year=is_latest_year(year),
        is_early_access=is_early_access(year),
    )


####################################################################
# MARK: 大会結果
####################################################################
# /year/resultはリダイレクト これによりresultページ内ですべての年度の結果を表示可能
@sitemapper.include(
    changefreq="yearly", priority=0.8, url_variables={"year": AVAILABLE_YEARS}
)
@app.route("/<int:year>/result")
def result(year: int):
    """
    結果ページを表示します。
    年度が指定されていない場合は最新年度を表示します。

    Args:
        year (int): 表示する年度

    Returns:
        Response: 結果のHTMLテンプレート
    """
    # 2022年度の場合はトップページへリダイレクト
    if year == 2022:
        return redirect(url_for("content", year=year, content="top"))

    # 引数を取得
    category = request.args.get("category")

    # カテゴリを取得（遅延読み込み対応）
    def get_result_categories_for_year(year):
        if year in ALL_CATEGORY_DICT:
            return ALL_CATEGORY_DICT[year]

        # 遅延読み込み：まだ読み込まれていない年度のデータを取得
        categories = persistent_cache.get_result_categories(year)
        ALL_CATEGORY_DICT[year] = categories  # キャッシュに保存
        return categories

    all_category = get_result_categories_for_year(year)
    if not all_category:
        return render_template(
            "/common/result.html",
            year=year,
            is_latest_year=is_latest_year(year),
            is_early_access=is_early_access(year),
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
        is_latest_year=is_latest_year(year),
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
def rule(year: int):
    """
    指定された年度のルールを表示します。
    年度が指定されていない場合は最新年度を表示します。

    Args:
        year (int): 表示する年度

    Returns:
        Response: ルールのHTMLテンプレート
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
        participants_list=participants_list,
        is_early_access=is_early_access(year),
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
    # 2022年度の場合はトップページへリダイレクト
    if year == 2022 and content != "top":
        return redirect(url_for("content", year=year, content="top"))

    # その他のページはそのまま表示
    try:
        return render_template(
            f"/{year}/{content}.html",
            year=year,
            is_latest_year=is_latest_year(year),
            is_early_access=is_early_access(year),
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
            is_latest_year=is_latest_year(year),
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
