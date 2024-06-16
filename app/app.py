from datetime import datetime

import pandas as pd
from flask import Flask, redirect, render_template, request, url_for

from app import key

app = Flask(__name__)
app.secret_key = key.SECRET_KEY


# /(年度) にアクセスしたときの処理
@app.route("/")
def route_top():
    year = datetime.now().year
    content = 'top'
    return redirect(url_for("content", year=year, content=content))


@app.route('/<int:year>/participants', methods=["GET"])
def participants(year: int = None):

    category = request.args.get("category")
    ticket_class = request.args.get("ticket_class")

    if category is None or ticket_class is None:
        if category is None:
            category = "Solo"
        if ticket_class is None:
            ticket_class = "all"
        return redirect(url_for('participants', year=year, category=category, ticket_class=ticket_class))

    # csvからデータを取得
    beatboxers_df = pd.read_csv(f'app/static/csv/gbb{year}_participants.csv')
    countries_df = pd.read_csv('app/static/csv/countries.csv')

    # Merge data to include country names in beatboxers_df
    beatboxers_df = beatboxers_df.merge(
        countries_df[['iso_code', 'name', "name_ja"]],
        on='iso_code',
        how='left',
        suffixes=('', '_country')
    )

    # フィルター処理
    # 部門でフィルター
    beatboxers_df = beatboxers_df[beatboxers_df['category'] == category]

    # 出場区分でフィルター
    if ticket_class == "wildcard":
        beatboxers_df = beatboxers_df[
            beatboxers_df['ticket_class'].str.startswith('Wildcard')
        ]

    elif ticket_class == "seed_right":
        beatboxers_df = beatboxers_df[
            ~beatboxers_df['ticket_class'].str.startswith('Wildcard')
        ]

    # フロントエンドに渡すデータを整形
    participant_front_list = []
    for _, row in beatboxers_df.iterrows():

        # キャンセルした人の場合
        if "[cancelled]" in row["name"]:

            participant = {
                "name": row["name"].replace("[cancelled] ", ""),
                "country": row["name_ja"],
                "ticket_class": row["ticket_class"],
                "is_cancelled": True
            }

        else:
            participant = {
                "name": row["name"],
                "country": row["name_ja"],
                "ticket_class": row["ticket_class"],
                "is_cancelled": False
            }
        participant_front_list.append(participant)

    # キャンセルした人をリストの最後に移動
    participant_front_list = sorted(
        participant_front_list,
        key=lambda x: x["is_cancelled"]
    )

    return render_template(f"/{year}/participants.html", participants=participant_front_list, year=year)


@app.route("/<int:year>/result")
def result(year: int = None):
    try:
        results_df = pd.read_csv(f'app/static/csv/gbb{year}_result.csv')
        results_df = results_df.fillna("-")

        # フロントエンドに渡すデータを整形
        results = []
        for _, row in results_df.iterrows():
            result = {
                "category": row["category"],
                "_1st": row["1"],
                "_2nd": row["2"],
                "_3rd": row["3"]
            }
            results.append(result)

    except pd.errors.EmptyDataError:
        results = None

    return render_template(f"/{year}/result.html", results=results, year=year)


@app.route("/<int:year>/<string:content>")
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
