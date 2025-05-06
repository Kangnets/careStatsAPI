# -*- coding: utf-8 -*-
import os
import sys
import json
import time
import math
import pandas as pd
import folium
from geopy.geocoders import Nominatim
import gspread
from google.oauth2 import service_account

def load_worksheet(index=1):
    """구글 스프레드시트 워크시트(index) → DataFrame"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    key_path = os.path.normpath(os.path.join(
        script_dir, "../key/datascience-457408-eb15d8611be3.json"
    ))
    info = json.load(open(key_path, encoding='utf-8'))
    info['private_key'] = info['private_key'].replace('\\n','\n')
    creds = service_account.Credentials.from_service_account_info(
        info, scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
    )
    client = gspread.authorize(creds)
    SPREADSHEET_ID = "1_m5GzATyDfHQ6GH_AIDt96dG-fUkLt-I4a93XlSkA58"
    ws = client.open_by_key(SPREADSHEET_ID).get_worksheet(index)
    df = pd.DataFrame(ws.get_all_records())
    df.columns = df.columns.str.strip()
    return df

def geocode_districts(districts):
    """시군구명 리스트 → {구명: (lat, lon)}"""
    geolocator = Nominatim(user_agent="bubble_map", timeout=10)
    coords = {}
    for d in districts:
        try:
            loc = geolocator.geocode(f"{d}, South Korea")
            coords[d] = (loc.latitude, loc.longitude) if loc else (None, None)
        except:
            coords[d] = (None, None)
        time.sleep(1)
    return coords

def main():
    # 1) 워크시트 로드 & 집계
    df = load_worksheet(index=1)
    # 반드시 컬럼명이 정확히 일치해야 합니다.
    if '시도' not in df.columns or '정원' not in df.columns:
        raise KeyError("워크시트에 '시도' 또는 '정원' 컬럼이 없습니다.")
    df = df[['시도','정원']].dropna(subset=['시도'])
    df['정원'] = pd.to_numeric(df['정원'], errors='coerce').fillna(0).astype(int)

    summary = (
        df
        .groupby('시도', as_index=False)['정원']
        .sum()
        .rename(columns={'정원':'총정원'})
    )
    print("=== 시군구별 총정원 ===")
    print(summary.to_string(), "\n")

    # 2) 지오코딩
    coords = geocode_districts(summary['시도'])

    # 3) 지도 생성
    m = folium.Map(location=[36,128], zoom_start=6, width='100%', height='100%')

    # 4) 버블 추가 (픽셀 반지름)
    # radius = sqrt(총정원) * factor
    factor = 1.0  # 좀 더 크게 보이도록 조정
    for _, row in summary.iterrows():
        name = row['시도']
        val  = row['총정원']
        lat, lon = coords.get(name, (None, None))
        if lat is None: continue
        radius = math.sqrt(val) * factor
        folium.CircleMarker(
            location=(lat, lon),
            radius=radius,
            color='darkgreen',
            fill=True,
            fill_color='lightgreen',
            fill_opacity=0.6,
            popup=folium.Popup(f"<b>{name}</b><br>총정원: {val}명", max_width=200)
        ).add_to(m)

    # 5) 범례(텍스트) 추가
    legend_html = """
     <div style="
       position: fixed;
       bottom: 50px;
       left: 50px;
       width: 240px;
       max-height: 400px;
       overflow: auto;
       border:2px solid grey;
       background-color: white;
       padding: 10px;
       font-size:14px;
       z-index:9999;
     ">
       <b>시군구별 총정원</b><br>
    """
    for _, row in summary.iterrows():
        legend_html += f"&nbsp;{row['시도']}: {row['총정원']}명<br>"
    legend_html += "</div>"
    m.get_root().html.add_child(folium.Element(legend_html))

    # 6) 지도 범위 자동 조정
    bounds = [coords[n] for n in summary['시도'] if coords[n][0] is not None]
    if bounds:
        m.fit_bounds(bounds)

    # 7) 저장
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "capacity_bubble_map.html")
    m.save(out)
    print(f"✅ 버블맵 저장: {out}")

if __name__ == "__main__":
    main()
