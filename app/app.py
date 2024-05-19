import hashlib
from datetime import datetime

import country_code
import pymysql
from flask import Flask, redirect, render_template, request, session, url_for

from app import key

app = Flask(__name__)
app.secret_key = key.SECRET_KEY

# MySQLへの接続設定
connection = pymysql.connect(
    host=key.HOST,
    user=key.USER,
    password=key.PASSWORD,
    db=key.DB
)


# /(年度) にアクセスしたときの処理
@app.route("/")
def route_top():
    year = datetime.now().year
    content = 'top'
    return redirect(url_for("content", year=year, content=content))


@app.route("/admin")
def admin():
    return render_template("admin.html")


@app.route('/<int:year>/participants', methods=["GET"])
def participants(year: int = None):

    if year is None:
        year = int(request.args.get("year"))
    category = request.args.get("category")
    ticket_class = request.args.get("ticket_class")

    if year is None:
        year = datetime.now().year

    cursor = connection.cursor()
    cursor.execute("SELECT * FROM participants")
    participants = cursor.fetchall()
    cursor.close()

    participant_front_list = []

    # 5と6を、7と8を統合する
    for participant in participants:

        participant_dict_tmp = {}

        year_ = participant[1]
        name = participant[2]
        category_ = participant[3]
        country = participant[4]
        seed_right = participant[5]
        wildcard = participant[6]
        cancelled = participant[7]
        move_up = participant[8]

        country_name_ja = country_code.get_country_name_from_code(country)

        if year_ != year or category_ != category:
            continue

        if ticket_class == "wildcard" and bool(wildcard) is False:
            continue

        if ticket_class == "seed_right" and bool(seed_right) is False:
            continue

        participant_dict_tmp["name"] = name
        participant_dict_tmp["country"] = country_name_ja

        # 出場権区分について
        if bool(seed_right):
            participant_dict_tmp["ticket_class"] = seed_right

        elif bool(wildcard):
            participant_dict_tmp["ticket_class"] = str(wildcard) + "位"

        else:
            participant_dict_tmp["ticket_class"] = "データなし"

        # 繰り上げ出場について
        if bool(move_up):
            participant_dict_tmp["ticket_class"] += " 繰上げ"

        # キャンセルは辞書のすべての要素に横線<s>を引く
        if bool(cancelled):
            participant_dict_tmp = {
                k: "<s>" + v + "</s>" for k, v in participant_dict_tmp.items()}
            participant_dict_tmp["name"] += " 辞退"

        participant_front_list.append(participant_dict_tmp)

    return render_template(f"/{year}/participants.html", participants=participant_front_list, year=year)


@app.route("/<int:year>/<string:content>")
def content(year: int = None, content: str = None):

    if year is None:
        year = datetime.now().year

    available_years = [2023, 2024]
    if year not in available_years:
        year = 2024

    if content == "participants":
        return redirect(url_for("participants", year=year))

    return render_template(f"/{year}/{content}.html", year=year)

###############################################################################
# 管理用機能


@app.route("/participants_dashboard")
def participants_dashboard():
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM participants")
    participants = cursor.fetchall()
    cursor.close()

    # participantsの要素を逆順にする
    participants = participants[::-1]

    # データを処理
    participant_list = [list(participant) for participant in participants]

    for participant in participant_list:
        participant[7] = str(bool(participant[7]))
        participant[8] = str(bool(participant[8]))

    return render_template("participants_dashboard.html", participants=participant_list)


@app.route("/login", methods=["post"])
def login():
    password = request.form["password"]
    hashed_password = hashlib.sha256(
        (password + key.SALT).encode("utf-8")).hexdigest()

    # ユーザー名とパスワードの検証
    with connection.cursor() as cursor:
        sql = "SELECT * FROM login WHERE hashed_pass=%s"
        cursor.execute(sql, hashed_password)
        user = cursor.fetchone()

    if user:
        session["user"] = user
        return redirect(url_for("dashboard"))


@app.route("/logout", methods=["post"])
def logout():
    session.pop("user", None)
    return redirect(url_for("admin"))


@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect(url_for("admin"))

    status = request.args.get("status")

    if status is None:
        status = "(´・ω・`)"

    return render_template("dashboard.html", status=status)


# GBB出場者の追加
@app.route("/add", methods=["post"])
def add():
    # カーソルを作成
    cursor = connection.cursor()

    if "user" not in session:
        return redirect(url_for("admin"))

    year = datetime.now().year
    name = request.form["name"]  # str
    category = request.form["category"]  # str
    country = request.form["country"]  # str 2文字のISO国コード 大文字
    seed_right = request.form["seed_right"]  # str or None (シード権を得た大会名)
    wildcard = request.form["wildcard"]  # int or None (順位)
    cancelled = False  # bool (キャンセルしたかどうか) addする時点ではFalse
    move_up = int(bool(request.form["move_up"]))  # bool  (繰り上げ出場かどうか)

    # 国の名前が正しいかどうかを確認
    # 台湾と入力されたら無条件で許可
    if country_code.is_valid_country_code(country) is False:
        return redirect(url_for("dashboard", status="国コードが正しくありません"))

    try:
        # SQLクエリを実行
        sql = "INSERT INTO participants (year, name, category, country, seed_right, wildcard, cancelled, move_up) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"
        values = (
            year, name, category, country, seed_right,
            wildcard, cancelled, move_up
        )
        cursor.execute(sql, values)

        # 変更をコミット
        connection.commit()

    except Exception as e:
        print(f"An error occurred: {e}")
        return redirect(url_for("dashboard", status=f"追加失敗: {e}"))

    return redirect(url_for("dashboard", status="追加完了"))


@app.route("/update", methods=["post"])
def update():
    # カーソルを作成
    cursor = connection.cursor()

    if "user" not in session:
        return redirect(url_for("admin"))

    year = datetime.now().year
    name = request.form["name"]
    category = request.form["category"]
    country = request.form["country"]
    seed_right = request.form["seed_right"]
    wildcard = request.form["wildcard"]
    cancelled = int(bool(request.form["cancelled"]))
    move_up = int(bool(request.form["move_up"]))
    id = request.form["id"]

    # 国の名前が正しいかどうかを確認
    if country_code.is_valid_country_code(country) is False:
        return redirect(url_for("dashboard", status="国コードが正しくありません"))

    try:
        sql = "UPDATE participants SET year=%s, name=%s, category=%s, country=%s, seed_right=%s, wildcard=%s, cancelled=%s, move_up=%s WHERE id=%s"
        values = (
            year, name, category, country, seed_right, wildcard, cancelled, move_up, id
        )
        cursor.execute(sql, values)

        connection.commit()

    except Exception as e:
        print(f"An error occurred: {e}")

    finally:
        cursor.close()

    return redirect(url_for("dashboard", status="更新完了"))


@app.route("/delete", methods=["post"])
def delete():
    cursor = connection.cursor()

    if "user" not in session:
        return redirect(url_for("admin"))

    id = request.form["id"]

    try:
        sql = "DELETE FROM participants WHERE id=%s"
        cursor.execute(sql, id)

        connection.commit()

    except Exception as e:
        print(f"An error occurred: {e}")

    finally:
        cursor.close()

    return redirect(url_for("dashboard", status="削除完了"))


if __name__ == "__main__":
    app.run(debug=True)
