import re

import folium
import mojimoji
import pandas as pd
import pykakasi
from rapidfuzz.process import extract

instagram = {
    2024: {
        "Solo": "https://www.instagram.com/p/C5MCF_QrlHd/?img_index=10",
        "Tag Team": "https://www.instagram.com/p/C5qoFKgtfR5/?img_index=8",
        "Loopstation": "https://www.instagram.com/p/C5JUKNUoYqk/?img_index=8",
        "Producer": "https://www.instagram.com/p/C5tIechNmah/?img_index=5",
        "Crew": "https://www.instagram.com/p/C5vtSWFtmiJ/?img_index=7",
    }
}

kakasi = pykakasi.kakasi()
kakasi.setMode("H", "a")  # ひらがなをローマ字に変換
kakasi.setMode("K", "a")  # カタカナをローマ字に変換
kakasi.setMode("J", "a")  # 漢字をローマ字に変換
converter = kakasi.getConverter()

# df事前準備
countries_df = pd.read_csv("app/static/csv/countries.csv")


def get_participants_list(
    year: int,
    category: str,
    ticket_class: str,
    cancel: str,
    GBB: bool = None,
    iso_code: int = None,
):
    """
    GBB参加者のリストを取得します。

    Args:
        year (int): 参加者の年。
        category (str): 参加者のカテゴリー。
        ticket_class (str): 出場権の種類。
        cancel (str, "show", "hide", "only_cancelled"): キャンセルの状態。
        GBB (bool, optional): GBBでのシード権の有無。
        iso_code (int, optional): 国コード。

    Returns:
        list: フィルタリングされた参加者のリスト。
    """
    global countries_df

    # csvからデータを取得 (ここの処理は毎回行う必要がある)
    beatboxers_df = pd.read_csv(f"app/static/csv/participants/{year}.csv")
    beatboxers_df = beatboxers_df.fillna("")

    # Merge data to include country names in beatboxers_df
    merged_df = beatboxers_df.merge(
        countries_df[["iso_code", "name", "name_ja"]],
        on="iso_code",
        how="left",
        suffixes=("", "_country"),
    )
    if merged_df.isnull().any().any():
        null_columns = merged_df.columns[merged_df.isnull().any()].tolist()
        null_rows = merged_df[merged_df.isnull().any(axis=1)]
        error_message = f"Merge operation resulted in NaN values in columns: {null_columns}. Rows with NaN values:\n{null_rows}"
        raise ValueError(error_message)
    beatboxers_df = merged_df

    # フィルター処理
    # 部門でフィルター
    if category != "all":
        beatboxers_df = beatboxers_df[beatboxers_df["category"] == category]

    # 出場区分がWildcardの人のみ表示
    if ticket_class == "wildcard":
        beatboxers_df = beatboxers_df[
            beatboxers_df["ticket_class"].str.startswith("Wildcard")
        ]

    # 出場区分がシード権の人のみ表示
    elif ticket_class == "seed_right":
        beatboxers_df = beatboxers_df[
            ~beatboxers_df["ticket_class"].str.startswith("Wildcard")
        ]

    # 国コードでフィルター
    if iso_code is not None:
        beatboxers_df = beatboxers_df[beatboxers_df["iso_code"] == iso_code]

    # GBBでシード権を獲得した人のみ表示
    if GBB is True:
        beatboxers_df = beatboxers_df[
            beatboxers_df["ticket_class"].str.startswith("GBB")
        ]

    # GBB以外でシード権を獲得した人のみ表示
    elif GBB is False:
        beatboxers_df = beatboxers_df[
            ~beatboxers_df["ticket_class"].str.startswith("GBB")
        ]

    # キャンセルした人のみを表示
    if cancel == "only_cancelled":
        beatboxers_df = beatboxers_df[
            beatboxers_df["name"].str.startswith("[cancelled]")
        ]

    # キャンセルした人を非表示
    if cancel == "hide":
        beatboxers_df = beatboxers_df[
            ~beatboxers_df["name"].str.startswith("[cancelled]")
        ]

    # フロントエンドに渡すデータを整形
    participants_list = []
    for _, row in beatboxers_df.iterrows():
        # キャンセルしたかのチェック
        is_cancelled = "[cancelled]" in row["name"]

        participant = {
            "name": row["name"].replace("[cancelled] ", "").upper(),
            "category": row["category"],
            "country": f"{row['name_ja']} {row['name_country']}",
            "ticket_class": row["ticket_class"],
            "is_cancelled": is_cancelled,
            "members": row["members"].upper(),
        }

        # すでに出場者リストに登録されており、countryが違う場合、もとの辞書に追加
        for p in participants_list:
            if (
                p["name"] == participant["name"]
                and p["country"] != participant["country"]
            ):
                p["country"] += f", {participant['country']}"
                break
        else:
            participants_list.append(participant)

    participants_list = sorted(
        participants_list,
        key=lambda x: (
            x["is_cancelled"],  # キャンセルした人を後ろに
            "発表" in x["name"],  # 未定の出場枠を後ろに
            x["category"],  # カテゴリー順
            # GBBから始まる人 (= GBBトップ3 or 優勝) を前に
            not x["ticket_class"].startswith("GBB"),
            x["ticket_class"].startswith("Wildcard"),  # Wildcardから始まる人を後ろに
            # Wildcardの場合、年度と順位でソート
            (
                int(
                    x["ticket_class"]
                    .replace("Wildcard ", "")
                    .replace("(", "")
                    .replace(")", "")
                    .split(" ")[1]
                )
                if len(x["ticket_class"].replace("Wildcard ", "").split(" ")) > 1
                else float("inf"),
                int(x["ticket_class"].replace("Wildcard ", "").split(" ")[0])
                if x["ticket_class"].startswith("Wildcard")
                and len(x["ticket_class"].replace("Wildcard ", "").split(" ")) > 1
                else float("inf"),
            )
            if x["ticket_class"].startswith("Wildcard")
            else (float("inf"), float("inf")),
            # Wildcard上位を前に
        ),
    )

    # 2020年のみ、名前順にソート
    if year == 2020:
        participants_list = sorted(participants_list, key=lambda x: x["name"])

    return participants_list


# キーワードで検索
def search_participants(year: int, keyword: str):
    """
    指定された年度の出場者をキーワードで検索します。

    Args:
        year (int): 検索対象の年度。
        keyword (str): 検索するキーワード。

    Returns:
        list: 一致した出場者のリスト。
    """
    # 全角・半角の表記ゆれを統一
    # 英数字を半角に変換
    keyword = mojimoji.han_to_zen(keyword, ascii=False, digit=True)

    # 日本語（カタカナ）を全角に変換
    keyword = mojimoji.zen_to_han(keyword, kana=False)

    # 入力が英数字表記かどうか判定
    # 記号も対象・Ωは"Sound of Sony Ω"の入力対策
    match_alphabet = re.match(
        r'^[a-zA-Z0-9 \-!@#$%^&*()_+=~`<>?,.\/;:\'"\\|{}[\]Ω]+', keyword
    )
    if match_alphabet is None:
        # ローマ字に変換
        keyword = converter.do(keyword)

    # 出場者リストを取得
    participants_list = get_participants_list(
        year=year, category="all", ticket_class="all", cancel="show"
    )
    participants_name_list = [participant["name"] for participant in participants_list]
    participants_members_list = [
        member.strip()
        for participant in participants_list
        for member in participant["members"].split(",")
    ]

    # キーワードで検索
    results_name = extract(
        keyword.upper(), participants_name_list, limit=5, score_cutoff=1
    )
    results_members = extract(
        keyword.upper(), participants_members_list, limit=5, score_cutoff=1
    )

    # 名前とmembersの結果を統合
    combined_results = {
        result[0]: result[1] for result in results_name + results_members
    }

    # 類似度が高い順に並び替え
    sorted_results = sorted(combined_results.items(), key=lambda x: x[1], reverse=True)

    # 名前だけに変換
    top_results = [result[0] for result in sorted_results]

    # resultsにある名前のデータを取得
    participants_search_result = []
    for result in top_results:
        # 1人の部門・チームの部門 (グループ名)
        participant_solos = [
            participant
            for participant in participants_list
            if participant["name"] == result
        ]
        participants_search_result.extend(participant_solos)

        # チームの部門 (メンバー名)
        participant_teams = [
            participant
            for participant in participants_list
            if result in participant["members"]
        ]
        participants_search_result.extend(participant_teams)

        if participant_solos == [] and participant_teams == []:
            print(f"\nError: {result} is not found in participants_list.\n")

    # 元の順序を保持しつつ、重複を削除、上位5件を取得
    final_result = [
        participants_search_result[i]
        for i in range(len(participants_search_result))
        if participants_search_result[i] not in participants_search_result[:i]
    ][:5]

    return final_result


def create_world_map(year: int):
    """
    指定された年の参加者の位置を示す世界地図を作成します。

    Args:
        year (int): 地図を作成する年。

    Returns:
        None (ファイルを保存)
    """
    # csvからデータを取得
    beatboxers_df = pd.read_csv(f"app/static/csv/participants/{year}.csv")

    # nanを空白に変換
    beatboxers_df = beatboxers_df.fillna("")

    # beatboxers_dfから、名前に[cancelled]がついている人を削除
    beatboxers_df = beatboxers_df[
        ~beatboxers_df["name"].str.contains(r"\[cancelled\]", case=False)
    ]

    # beatboxers_dfから、国コード0の人を削除
    beatboxers_df = beatboxers_df[beatboxers_df["iso_code"] != 0]

    # beatboxers_dfを、カテゴリーでソート
    beatboxers_df = beatboxers_df.sort_values(by=["category"])

    # Initialize a folium map centered around the average latitude and longitude
    map_center = [20, 0]
    beatboxer_map = folium.Map(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Physical_Map/MapServer/tile/{z}/{y}/{x}",
        attr="Tiles &copy; Esri &mdash; Source: US National Park Service",
        location=map_center,
        zoom_start=2,
        zoom_control=True,
        control_scale=True,
        min_zoom=1,
        max_zoom=8,
        max_bounds=True,
        options={
            "zoomSnap": 0.1,  # ズームのステップを0.1に設定
            "zoomDelta": 0.1,  # ズームの増減を0.1に設定
        },
    )

    # Merge data to include country coordinates in beatboxers_df
    beatboxers_df = beatboxers_df.merge(
        countries_df[["iso_code", "lat", "lon", "name"]],
        on="iso_code",
        how="left",
        suffixes=("", "_country"),
    )

    # 国ごとに参加者をグループ化
    coord_participants = beatboxers_df.groupby(["lat", "lon"])

    # Add markers to the map
    # 国ごとにまとめてマーカーを追加
    for (lat, lon), group in coord_participants:
        names = group["name"].values
        categories = group["category"].values
        members = group["members"].values

        # チーム数
        len_group = len(names)

        # beatboxer数
        beatboxers = []
        for name, member_names in zip(names, members):
            if member_names:
                beatboxers.extend(member_names.upper().split(", "))
            else:
                beatboxers.append(name.upper())

        unique_beatboxers = set(beatboxers)
        len_beatboxers = len(unique_beatboxers)

        country_name = group["name_country"].values[0]
        iso_code = group["iso_code"].values[0]

        # 国名を日本語に変換
        # countries_dfからiso_codeが一致する行を取得
        country_data = countries_df[countries_df["iso_code"] == iso_code]
        country_name_ja = country_data["name_ja"].values[0]

        location = (lat, lon)

        popup_content = '<div style="font-family: \'Noto sans JP\'; font-size: 14px;">'
        popup_content += f"""
        <h3 style="margin: 0; color: #F0632F;">
            {country_name}
        </h3>
        """
        popup_content += f"""
        <h4 style="margin: 0; color: #F0632F;">
            {len_group} teams<br>{len_beatboxers} beatboxers<br>{country_name_ja}
        </h4>
        """

        if year == 2020:
            sorted_names_with_category = sorted(
                zip(names, categories, members), key=lambda x: (x[1], x[0])
            )

            names, categories, members = zip(*sorted_names_with_category)

        for name, category, member_names in zip(names, categories, members):
            if member_names != "":
                popup_content += f"""
                <p style="margin: 5px 0;">
                    <strong style="color: #000000">{name.upper()}</strong> ({category})<span style="font-size: 0.7em; color=#222222"><br>【{member_names.upper()}】</span>
                </p>
                """
            else:
                popup_content += f"""
                <p style="margin: 5px 0;">
                    <strong style="color: #000000">{name.upper()}</strong> ({category})
                </p>
                """

        popup_content += "</div>"

        if len_group > 7:
            popup_content = f'<div style="font-family: \'Noto sans JP\'; font-size: 14px; max-height: 300px; overflow-y: scroll;">{popup_content}</div>'

        # アイコン素材がある国の場合
        icon_size = (48, 48)
        icon_anchor = (24, 48)

        popup = folium.Popup(popup_content, max_width=1000)

        flag_icon = folium.CustomIcon(
            icon_image=r"app/static/images/flags/"
            + country_name
            + ".webp",  # アイコン画像のパス
            icon_size=icon_size,  # アイコンのサイズ（幅、高さ）
            icon_anchor=icon_anchor,  # アイコンのアンカー位置
        )

        folium.Marker(
            location=location,
            popup=popup,
            tooltip=f"{country_name} / {country_name_ja}",
            icon=flag_icon,
        ).add_to(beatboxer_map)

    beatboxer_map.save(f"app/templates/{year}/world_map.html")
