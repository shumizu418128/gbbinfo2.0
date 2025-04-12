このサイトの詳しい説明はこちら：
[GBBINFO-JPNの設計図](https://qiita.com/tari3210/items/0561e91774863d165af0)

株式会社サポーターズ様 主催イベント「技育博 2024 Vol.5」出場作品
```
.
├── .gitignore  // Gitの管理対象外ファイルを指定
├── Dockerfile  // Dockerイメージの定義ファイル
├── README.md  // プロジェクトの概要や説明
├── app  // アプリケーションの主要なコード
├── .well-known  // Webサイトの認証や設定に関する情報
│   └── discord  // Discord連携に関する設定
├── __init__.py  // Pythonパッケージの初期化ファイル
├── ads.txt  // デジタル広告に関する情報
├── babel.cfg  // Babel（国際化ライブラリ）の設定ファイル
├── database  // データベース関連ファイル
│   ├── countries.csv  // 国名と国コードの対応表
│   ├── participants  // 出場者データ
│   │   └── [year].csv (for years 2013-2017, 2018-2021, 2023-2025)  // 年ごとの出場者データ（CSV形式）
│   └── result  // 大会結果データ
│       └── [competition_type].csv and [year] (for 2017-2021, 2023-2024)  // 大会タイプと年ごとの結果データ（CSV形式）
├── favicon.ico  // ファビコン（Webサイトのアイコン）
├── icon_512.png  // PWA用アイコン（512x512）
├── json  // JSONデータ関連ファイル
│   └── cache.json  // キャッシュデータ（JSON形式）
├── main.py  // アプリケーションのエントリーポイント
├── manifest.json  // PWAマニフェストファイル
├── messages.pot  // gettextの翻訳テンプレートファイル
├── modules  // アプリケーションのモジュール
│   └── [module].py (config, gemini, participants, result, spreadsheet, translate)  // 各モジュール（設定、Gemini連携、出場者、結果、スプレッドシート、翻訳）
├── naver.html  // Naver Webmaster Tool認証ファイル
├── prompt.txt  // プロンプトテキスト
├── robots.txt  // クローラーの制御ファイル
├── service-worker.js  // PWAサービスワーカー
├── static  // 静的ファイル（CSS、JavaScript、画像など）
│   ├── css  // CSSファイル
│   │   └── [css_file].css (base, components, search, table)  // 各CSSファイル（ベース、コンポーネント、検索、テーブル）
│   ├── favicon.ico  // ファビコン
│   ├── icon.png  // アイコン
│   ├── icon_512.png  // PWA用アイコン
│   ├── images  // 画像ファイル
│   │   ├── background.webp  // 背景画像
│   │   ├── button  // ボタン画像
│   │   │   └── [button_image].webp (afterparty, bitomori, dice, h1, hug, inkie, scott_jackson, sinjo, sorry, venue, winner, zenhit)  // 各ボタン画像
│   │   ├── flags  // 国旗画像
│   │   │   └── country.webp  // 各国旗画像
│   │   ├── header.webp  // ヘッダー画像
│   │   └── icon  // アイコン画像
│   │       └── [icon_image].webp (icon-arrow, icon-close, icon-home, icon-search)  // 各アイコン画像
│   ├── screenshot.png  // スクリーンショット
│   └── scripts  // JavaScriptファイル
│       └── [javascript_file].js (analysis, navigation, search_function, timer, ui)  // 各JavaScriptファイル（分析、ナビゲーション、検索機能、タイマー、UI）
├── templates  // HTMLテンプレートファイル
│   ├── [year]  // 年ごとのテンプレート
│   │   └── [template_file].html or memo.txt (for years 2013-2021, 2022-2025)  // 各テンプレートファイルまたはメモ
│   ├── base.html  // 基本テンプレート
│   ├── common  // 共通テンプレート
│   │   └── [common_template].html (404, japan, participants, result)  // 各共通テンプレート（404エラー、日本、出場者、結果）
│   ├── includes  // include用テンプレート
│   │   └── [include_template].html (bottom_navigation, early_access, ended, participants_form, popup_early_access, popup_ended, popup_no_info)  // 各include用テンプレート
│   └── others  // その他のテンプレート
│       └── [other_template].html (7tosmoke, about, analysis, how_to_plan, past_info, result_stream, translation, url_change)  // 各その他テンプレート
├── translations  // 翻訳ファイル
│   └── [language_code]  // 言語コード
│       └── LC_MESSAGES  // メッセージカタログ
│           ├── messages.mo  // コンパイル済み翻訳ファイル
│           └── messages.po  // 翻訳ファイル（編集用）
├── requirements.txt  // Pythonの依存ライブラリ
└── run.py  // アプリケーションの実行ファイル
```

### メモ
- 2023年のみ、ruleページと出場者データ未接続
- csvには出場者未定のシード権も記入
  - その際、出場者名は「～?/? 発表～」とする
  - 出身国が不明の場合、国コードは0とする
    - 国コード0はcountry.csvに追加済み
    - 国コード0の場合、world_mapには表示されない
