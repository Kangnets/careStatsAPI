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

def load_worksheet(index=2):
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

def geocode_regions(regions):
    """시도명 리스트 → {시도명: (lat, lon)}"""
    geolocator = Nominatim(user_agent="bubble_map", timeout=10)
    coords = {}
    for r in regions:
        loc = geolocator.geocode(f"{r}, 서울특별시, South Korea")
        if loc:
            coords[r] = (loc.latitude, loc.longitude)
        else:
            coords[r] = (None, None)
        time.sleep(1)
    return coords

def main():
    # 1) 워크시트 로드 & 집계
    df = load_worksheet(index=2)
    df = df[df['통계시도명'] == '서울특별시'] # 서울만
    if '통계시군구명' not in df.columns or '지급건수' not in df.columns:
        raise KeyError("워크시트에 '통계시군구명' 또는 '지급건수' 컬럼이 없습니다.")
    df = df[['통계시군구명','지급건수']].dropna(subset=['통계시군구명'])
    df['지급건수'] = pd.to_numeric(df['지급건수'], errors='coerce').fillna(0).astype(int)

    summary = (
        df
        .groupby('통계시군구명', as_index=False)['지급건수']
        .sum()
        .rename(columns={'지급건수':'총지급건수'})
    )

    print("=== 시군구별 총 지급건수 ===")
    print(summary.to_string(), "\n")

    # 2) 지오코딩 (시도 단위)
    coords = geocode_regions(summary['통계시군구명'])

    # 3) Folium 맵 생성
    m = folium.Map(location=[36, 128], zoom_start=6, width='100%', height='100%')

    # 4) 버블 추가 (크기 조정)
    #    radius = sqrt(총지급건수) * factor
    factor = 0.2 # 이전 0.5에서 축소
    for _, row in summary.iterrows():
        region = row['통계시군구명']
        count  = row['총지급건수']
        lat, lon = coords.get(region, (None, None))
        if lat is None:
            continue
        radius = math.sqrt(count) * factor
        folium.CircleMarker(
            location=(lat, lon),
            radius=radius,
            color='darkblue',
            fill=True,
            fill_color='lightblue',
            fill_opacity=0.6,
            popup=folium.Popup(f"<b>{region}</b><br>총지급건수: {count}건", max_width=200)
        ).add_to(m)

    # 5) 범례(텍스트) 추가
    legend_html = """
     <div style="
       position: fixed;
       bottom: 20px;
       left: 20px;
       width: 220px;
       max-height: 600px;
       overflow: auto;
       border:2px solid grey;
       background-color: white;
       padding: 10px;
       font-size:14px;
       z-index:9999;
     ">
       <b>서울특별시 구별 총지급건수</b><br>
    """
    for _, row in summary.iterrows():
        legend_html += f"&nbsp;{row['통계시군구명']}: {row['총지급건수']}건<br>"
    legend_html += "</div>"
    m.get_root().html.add_child(folium.Element(legend_html))

    # 6) 범위 자동 조정
    bounds = [coords[r] for r in summary['통계시군구명'] if coords[r][0] is not None]
    if bounds:
        m.fit_bounds(bounds)

    # 7) 저장
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bubble_map_by_region.html")
    m.save(out)
    print(f"✅ 시군구별 버블맵 저장: {out}")

if __name__ == "__main__":
    main()
