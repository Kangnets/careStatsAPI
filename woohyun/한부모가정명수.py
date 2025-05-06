# -*- coding: utf-8 -*-
import os
import time
import math
import pandas as pd
import folium
from geopy.geocoders import Nominatim
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

SPREADSHEET_ID = "1_m5GzATyDfHQ6GH_AIDt96dG-fUkLt-I4a93XlSkA58"

def load_data():
    """Worksheet index=7, A3:D 끝까지 읽어서 '계→소계' 시도별 데이터만 반환"""
    base = os.path.dirname(__file__)
    creds = Credentials.from_service_account_file(
        os.path.join(base, "../key/datascience-457408-eb15d8611be3.json"),
        scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
    )
    service = build('sheets', 'v4', credentials=creds)
    meta = service.spreadsheets().get(spreadsheetId=SPREADSHEET_ID).execute()
    sheet = meta['sheets'][7]['properties']['title']
    resp = service.spreadsheets().values().get(
        spreadsheetId=SPREADSHEET_ID,
        range=f"{sheet}!A3:D"
    ).execute()
    vals = resp.get('values', [])
    header = [c.strip() for c in vals[0]]
    rows = vals[1:]
    df = pd.DataFrame(rows, columns=header)
    df.columns = ['시도','특성1','특성2','수급자수']
    df = df[(df['특성1']=='계') & (df['특성2']=='소계') & (df['시도']!='계')]
    df['수급자수'] = df['수급자수'].str.replace(',', '').astype(int)
    return df[['시도','수급자수']]

def geocode(regions):
    geo = Nominatim(user_agent="sheet7_map", timeout=10)
    coords = {}
    for r in regions:
        try:
            loc = geo.geocode(f"{r}, South Korea")
            coords[r] = (loc.latitude, loc.longitude) if loc else (None, None)
        except:
            coords[r] = (None, None)
        time.sleep(1)
    return coords

def make_map(df):
    coords = geocode(df['시도'])
    m = folium.Map(location=[36,128], zoom_start=6, width='100%', height='100%')
    factor = 0.3

    # 1) 버블 추가
    for _, row in df.iterrows():
        lat, lon = coords[row['시도']]
        if lat is None: continue
        r = math.sqrt(row['수급자수']) * factor
        folium.CircleMarker(
            location=(lat, lon),
            radius=r,
            color='crimson',
            fill=True, fill_color='crimson', fill_opacity=0.6,
            popup=f"{row['시도']}: {row['수급자수']:,}명"
        ).add_to(m)

    # 2) 버블 크기 범례 (작·중·대)
    counts = df['수급자수']
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

    # 3) 텍스트 범례 (전체 시도별 수치)
    text_legend = '<div style="position:fixed;bottom:20px;right:20px;max-height:300px;overflow:auto;background:white;padding:8px;border:1px solid gray;font-size:12px;z-index:9999;">'
    text_legend += '<b>시도별 수급자수</b><br>'
    for _, row in df.iterrows():
        text_legend += f"{row['시도']}: {row['수급자수']:,}명<br>"
    text_legend += '</div>'

    m.get_root().html.add_child(folium.Element(bubble_legend + text_legend))

    # 4) 모든 버블 포함하도록 확대
    bounds = [coords[r] for r in df['시도'] if coords[r][0] is not None]
    if bounds:
        m.fit_bounds(bounds)

    out = os.path.join(os.path.dirname(__file__), "sheet7_bubble_map.html")
    m.save(out)
    print(f"✅ 맵 저장됨: {out}")

def main():
    df = load_data()
    make_map(df)

if __name__ == "__main__":
    main()
