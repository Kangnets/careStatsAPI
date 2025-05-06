# -*- coding: utf-8 -*-
import os
import json
import time
import math
import pandas as pd
import folium
import gspread
from geopy.geocoders import Nominatim
from google.oauth2.service_account import Credentials
from google.oauth2 import service_account

SPREADSHEET_ID = "1_m5GzATyDfHQ6GH_AIDt96dG-fUkLt-I4a93XlSkA58"

def load_data(index = 3):
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
    
    # 데이터 정리
    df = df[df['통계시도명'] == '서울특별시']
    df = (
        df
        .groupby('통계시군구명', as_index=False)['수급자수']
        .sum()
        .rename(columns={'수급자수':'총수급자수'})
    )
    
    return df

def geocode(regions):
    geo = Nominatim(user_agent="sheet3_map", timeout=10)
    coords = {}
    for r in regions:
        try:
            loc = geo.geocode(f"{r}, 서울특별시, South Korea")
            coords[r] = (loc.latitude, loc.longitude) if loc else (None, None)
        except:
            coords[r] = (None, None)
        time.sleep(1)
    return coords

def make_map(df):
    coords = geocode(df['통계시군구명'])
    m = folium.Map(location=[36,128], zoom_start=6, width='100%', height='100%')
    factor = 0.6

    # 1) 버블 추가
    for _, row in df.iterrows():
        lat, lon = coords[row['통계시군구명']]
        if lat is None: continue
        r = math.sqrt(row['총수급자수']) * factor
        folium.CircleMarker(
            location=(lat, lon),
            radius=r,
            color='crimson',
            fill=True, fill_color='crimson', fill_opacity=0.6,
            popup=f"{row['통계시군구명']}: {row['총수급자수']:,}명"
        ).add_to(m)

    # 2) 버블 크기 범례 (작·중·대)
    counts = df['총수급자수']
    example_counts = sorted({int(counts.min()), int(counts.median()), int(counts.max())})
    bubble_legend = '<div style="position:fixed;bottom:20px;left:20px;background:white;padding:8px;border:1px solid gray;font-size:12px;z-index:9999;">'
    bubble_legend += '<b>버블 크기 범례</b><br>'
    for cnt in example_counts:
        diam = math.sqrt(cnt) * factor * 2
        bubble_legend += (
            f'<span style="display:inline-block;'
            f'width:{diam}px;height:{diam}px;'
            f'background:crimson;border-radius:50%;opacity:0.6;vertical-align:middle;"></span> '
            f'{cnt:,}명<br>'
        )
    bubble_legend += '</div>'

    # 3) 텍스트 범례 (전체 구별 수치)
    text_legend = '<div style="position:fixed;bottom:20px;right:20px;max-height:600px;overflow:auto;background:white;padding:8px;border:1px solid gray;font-size:12px;z-index:9999;">'
    text_legend += '<b>서울특별시 구별 수급자수</b><br>'
    for _, row in df.iterrows():
        text_legend += f"{row['통계시군구명']}: {row['총수급자수']:,}명<br>"
    text_legend += '</div>'

    m.get_root().html.add_child(folium.Element(bubble_legend + text_legend))

    # 4) 모든 버블 포함하도록 확대
    bounds = [coords[r] for r in df['통계시군구명'] if coords[r][0] is not None]
    if bounds:
        m.fit_bounds(bounds)

    out = os.path.join(os.path.dirname(__file__), "sheet3_bubble_map.html")
    m.save(out)
    print(f"✅ 맵 저장됨: {out}")

def main():
    df = load_data()
    make_map(df)

if __name__ == "__main__":
    main()
