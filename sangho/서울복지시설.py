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
            loc = geolocator.geocode(f"{d}, 서울특별시, South Korea")
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
    # 서울의 모든 구 리스트
    seoul_gu_list = [
        '강남구', '강동구', '강북구', '강서구', '관악구', '광진구', '구로구', '금천구', 
        '노원구', '도봉구', '동대문구', '동작구', '마포구', '서대문구', '서초구', '성동구', 
        '성북구', '송파구', '양천구', '영등포구', '용산구', '은평구', '종로구', '중구', '중랑구'
    ]
    # '시도'와 '구'가 NaN인 행 제거
    df = df[['시도','정원', '구']].dropna(subset=['시도', '구'])
    df = df[(df['시도'].str.strip() != '') & (df['구'].str.strip() != '')]
    # 서울의 구 목록에 있는 모든 구를 데이터프레임에 추가
    missing_gu = [gu for gu in seoul_gu_list if gu not in df['구'].values]

    # 누락된 구들을 빈 값으로 추가 (정원은 0으로 설정)
    missing_df = pd.DataFrame({
        '시도': ['서울'] * len(missing_gu),
        '구': missing_gu,
        '정원': [0] * len(missing_gu)
    })

    # 기존 df와 누락된 구 데이터프레임 합치기
    df = pd.concat([df, missing_df], ignore_index=True)

    # 정원 컬럼 숫자 형식으로 변환
    df['정원'] = pd.to_numeric(df['정원'], errors='coerce').fillna(0).astype(int)
    # 서울만
    df = df[df['시도'] == '서울']
    # 정리
    summary = (
        df
        .groupby('구', as_index=False)['정원']
        .sum()
        .rename(columns={'정원':'총정원'})
    )
    print("=== 구별 총정원 ===")
    print(summary.to_string(), "\n")

    # 2) 지오코딩
    coords = geocode_districts(summary['구'])

    # 3) 지도 생성
    m = folium.Map(location=[36,128], zoom_start=6, width='100%', height='100%')

    # 4) 버블 추가 (픽셀 반지름)
    # radius = sqrt(총정원) * factor
    factor = 4.0  # 좀 더 크게 보이도록 조정
    for _, row in summary.iterrows():
        name = row['구']
        val  = row['총정원']
        lat, lon = coords.get(name, (None, None))
        if lat is None or val == 0: continue
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
       max-height: 600px;
       overflow: auto;
       border:2px solid grey;
       background-color: white;
       padding: 10px;
       font-size:14px;
       z-index:9999;
     ">
       <b>서울특별시 구별 복지시설 총정원</b><br>
    """
    for _, row in summary.iterrows():
        legend_html += f"&nbsp;{row['구']}: {row['총정원']}명<br>"
    legend_html += "</div>"
    m.get_root().html.add_child(folium.Element(legend_html))

    # 6) 지도 범위 자동 조정
    bounds = [coords[n] for n in summary['구'] if coords[n][0] is not None]
    if bounds:
        m.fit_bounds(bounds)

    # 7) 저장
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "capacity_bubble_map.html")
    m.save(out)
    print(f"✅ 버블맵 저장: {out}")

if __name__ == "__main__":
    main()
