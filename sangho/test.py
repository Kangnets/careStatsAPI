# -*- coding: utf-8 -*-
import os
import time
import json
import pandas as pd
import plotly.graph_objects as go
import gspread
from google.oauth2.service_account import Credentials
from geopy.geocoders import Nominatim

def get_coords(address):
    """주소 → (위도, 경도) 반환 (Nominatim 지오코딩)"""
    geolocator = Nominatim(user_agent="geoapi", timeout=10)
    try:
        time.sleep(0.5)
        loc = geolocator.geocode(address)
        if loc:
            return loc.latitude, loc.longitude
    except:
        pass
    return None, None

def load_sheet_data():
    """스프레드시트 A3:B23 읽어 DataFrame 반환"""
    base = os.path.dirname(os.path.abspath(__file__))
    key_path = os.path.join(base, "../key/datascience-457408-eb15d8611be3.json")
    if not os.path.exists(key_path):
        raise FileNotFoundError(f"키 파일을 찾을 수 없습니다: {key_path}")

    # 인증
    creds = Credentials.from_service_account_file(
        key_path,
        scopes=[
            "https://www.googleapis.com/auth/spreadsheets.readonly",
            "https://www.googleapis.com/auth/drive.readonly"
        ]
    )
    client = gspread.authorize(creds)

    # 워크시트 로드 (인덱스 4)
    SPREADSHEET_ID = "1_m5GzATyDfHQ6GH_AIDt96dG-fUkLt-I4a93XlSkA58"
    ws = client.open_by_key(SPREADSHEET_ID).get_worksheet(4)

    # A3:B23 범위 읽기
    raw = ws.get('A3:B23')
    header = [c.strip() for c in raw[2]]       # 3번째 행(A3,B3)을 헤더로
    rows   = raw[3:]                            # 4행부터 데이터
    df = pd.DataFrame(rows, columns=header)

    # 컬럼명 통일
    df.columns = ['지역', '한부모 가구 수']
    df['지역'] = df['지역'].astype(str).str.strip()
    df['한부모 가구 수'] = pd.to_numeric(df['한부모 가구 수'], errors='coerce').fillna(0).astype(int)
    return df

def make_bubble_map(df):
    """Plotly로 버블맵 생성 후 HTML로 저장"""
    # 서울특별시 기준 지오코딩
    df[['lat','lon']] = df['지역'].apply(
        lambda x: pd.Series(get_coords(f"서울특별시 {x}"))
    )

    # 버블 크기: max 기준 정규화 + 최소 크기
    max_cnt = df['한부모 가구 수'].max()
    df['size'] = df['한부모 가구 수'] / max_cnt * 40 + 5

    fig = go.Figure(
        go.Scattergeo(
            lon = df['lon'],
            lat = df['lat'],
            text= df['지역'] + '<br>' + df['한부모 가구 수'].astype(str) + ' 가구',
            marker=dict(
                size=df['size'],
                color='skyblue',
                line_color='darkblue',
                line_width=1,
                sizemode='diameter',
                opacity=0.7
            ),
            name='한부모 가구 수'
        )
    )

    fig.update_layout(
        title_text="서울시 지역별 한부모 가구 수 버블맵",
        showlegend=True,
        legend=dict(
            title="범례",
            x=0.9, y=0.95,
            bgcolor='rgba(255,255,255,0.7)',
            bordercolor='gray', borderwidth=1
        ),
        geo=dict(
            scope='asia',
            projection_type='mercator',
            showland=True,
            landcolor="rgb(243,243,243)",
            showcountries=False,
            center=dict(lat=37.55, lon=126.98),
            lataxis_range=[37.4, 37.8],
            lonaxis_range=[126.7, 127.3]
        ),
        height=700,
    )

    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "single_parent_bubble_map.html")
    fig.write_html(out_path, include_plotlyjs='cdn')
    print(f"✅ HTML 파일 저장됨: {out_path}")

def main():
    df = load_sheet_data()
    make_bubble_map(df)

if __name__ == "__main__":
    main()
