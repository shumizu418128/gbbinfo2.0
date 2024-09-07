import folium
import pandas as pd


def get_participants_list(year: int, category: str, ticket_class: str, cancel: str, GBB: bool = None, iso_code: int = None) -> list:
    # csvからデータを取得
    beatboxers_df = pd.read_csv(f'app/static/csv/{year}_participants.csv')
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
    if category != "all":
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

    # 国コードでフィルター
    if iso_code is not None:
        beatboxers_df = beatboxers_df[beatboxers_df['iso_code'] == iso_code]

    # GBBでシード権を獲得した人のみ表示
    if GBB is True:
        beatboxers_df = beatboxers_df[
            beatboxers_df['ticket_class'].str.startswith('GBB')
        ]

    # GBB以外でシード権を獲得した人のみ表示
    elif GBB is False:
        beatboxers_df = beatboxers_df[
            ~beatboxers_df['ticket_class'].str.startswith('GBB')
        ]

    # フロントエンドに渡すデータを整形
    participants_list = []
    for _, row in beatboxers_df.iterrows():

        # キャンセルした人の場合
        if "[cancelled]" in row["name"]:
            participant = {
                "name": row["name"].replace("[cancelled] ", "").upper(),
                "category": row["category"],
                "country": row["name_ja"],
                "ticket_class": row["ticket_class"],
                "is_cancelled": True
            }

        else:
            participant = {
                "name": row["name"].upper(),
                "category": row["category"],
                "country": row["name_ja"],
                "ticket_class": row["ticket_class"],
                "is_cancelled": False
            }

        # membersがNaNの場合があるため、その場合は空文字に変換
        if pd.isna(row["members"]):
            participant["members"] = ""
        else:
            participant["members"] = row["members"].upper()

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
            int(x["ticket_class"].replace("Wildcard ", ""))
            if x["ticket_class"].startswith("Wildcard") else float('inf')
            # Wildcard上位を前に
        )
    )

    # cancelが"hide"の場合はキャンセルした人を表示しない
    if cancel == "hide":
        participants_list = [
            participant for participant in participants_list if participant["is_cancelled"] is False]

    # cancelが"only_cancelled"の場合はキャンセルした人のみ表示
    if cancel == "only_cancelled":
        participants_list = [
            participant for participant in participants_list if participant["is_cancelled"] is True]

    return participants_list


def get_results(year: int) -> list:

    try:
        results_df = pd.read_csv(f'app/static/csv/{year}_result.csv')
        results_df = results_df.fillna("-")

        # フロントエンドに渡すデータを整形
        results = []
        for _, row in results_df.iterrows():
            result = {
                "category": row["category"],
                "_1st": row["1"].upper(),
                "_2nd": row["2"].upper(),
                "_3rd": row["3"].upper()
            }
            results.append(result)

    except pd.errors.EmptyDataError:
        results = None

    return results


def create_world_map(year: int):

    # csvからデータを取得
    beatboxers_df = pd.read_csv(f'app/static/csv/{year}_participants.csv')
    countries_df = pd.read_csv('app/static/csv/countries.csv')

    # nanを空白に変換
    beatboxers_df = beatboxers_df.fillna("")

    # beatboxers_dfから、名前に[cancelled]がついている人を削除
    beatboxers_df = beatboxers_df[~beatboxers_df["name"].str.contains(
        r"\[cancelled\]", case=False)]

    # beatboxers_dfから、国コード0の人を削除
    beatboxers_df = beatboxers_df[beatboxers_df["iso_code"] != 0]

    # beatboxers_dfを、カテゴリーでソート
    beatboxers_df = beatboxers_df.sort_values(by=["category"])

    # Initialize a folium map centered around the average latitude and longitude
    map_center = [20, 0]
    beatboxer_map = folium.Map(
        location=map_center,
        zoom_start=2,
        zoom_control=True,
        control_scale=True,
        min_zoom=1,
        max_bounds=True,
        options={
            'zoomSnap': 0.1,  # ズームのステップを0.1に設定
            'zoomDelta': 0.1,  # ズームの増減を0.1に設定
        }
    )

    # Merge data to include country coordinates in beatboxers_df
    beatboxers_df = beatboxers_df.merge(
        countries_df[['iso_code', 'lat', 'lon', 'name']],
        on='iso_code',
        how='left',
        suffixes=('', '_country')
    )

    # 国ごとに参加者をグループ化
    coord_participants = beatboxers_df.groupby(['lat', 'lon'])

    # Add markers to the map
    # 国ごとにまとめてマーカーを追加
    for (lat, lon), group in coord_participants:

        names = group["name"].values
        categories = group["category"].values
        members = group["members"].values

        country_name = group["name_country"].values[0]
        iso_code = group["iso_code"].values[0]

        # 国名を日本語に変換
        # countries_dfからiso_codeが一致する行を取得
        country_data = countries_df[countries_df["iso_code"] == iso_code]
        country_name_ja = country_data["name_ja"].values[0]

        location = (lat, lon)

        popup_content = '<div style="font-family: Noto sans JP; font-size: 14px;">'
        popup_content += f'<h3 style="margin: 0; color: #F0632F;">{
            country_name}</h3>'
        popup_content += f'<h4 style="margin: 0; color: #F0632F;">{
            country_name_ja}</h4>'

        for name, category, members in zip(names, categories, members):
            if members != "":
                popup_content += f'''
                <p style="margin: 5px 0;">
                    <strong style="color: #000000">{name.upper()}</strong> ({category})<span style="font-size: 0.7em; color=#222222"><br>【{members.upper()}】</span>
                </p>
                '''
            else:
                popup_content += f'''
                <p style="margin: 5px 0;">
                    <strong style="color: #000000">{name.upper()}</strong> ({category})
                </p>
                '''

        popup_content += '</div>'

        # アイコン素材がある国の場合
        icon_size = (48, 48)
        icon_anchor = (24, 48)

        popup = folium.Popup(popup_content, max_width=1000)

        flag_icon = folium.CustomIcon(
            icon_image=r"app/static/images/flags/" + country_name + ".webp",  # アイコン画像のパス
            icon_size=icon_size,  # アイコンのサイズ（幅、高さ）
            icon_anchor=icon_anchor  # アイコンのアンカー位置
        )

        folium.Marker(
            location=location,
            popup=popup,
            tooltip=f"{country_name} / {country_name_ja}",
            icon=flag_icon
        ).add_to(beatboxer_map)

    beatboxer_map.save(f"app/templates/{year}/world_map.html")
