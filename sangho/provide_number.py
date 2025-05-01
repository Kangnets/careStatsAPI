import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import time
import plotly.express as px
from geopy.geocoders import Nominatim
import plotly.graph_objects as go

# 지오코딩
geolocator = Nominatim(user_agent="geoapi")

def get_coords(address):
    try:
        time.sleep(0.5)
        location = geolocator.geocode(address)
        if location:
            print(f"주소 찾음: {address}")
            return pd.Series([location.latitude, location.longitude])
        else:
            print(f"⚠️ 주소를 찾을 수 없음: {address}")
            return pd.Series([None, None])
    except:
        return pd.Series([None, None])
        
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]
credentials_path = os.getenv("GOOGLE_SERVICE_ACCOUNT_KEY")
print(credentials_path)
credentials = ServiceAccountCredentials.from_json_keyfile_name(credentials_path, scope)

client = gspread.authorize(credentials)

spreadsheet_id = "1_m5GzATyDfHQ6GH_AIDt96dG-fUkLt-I4a93XlSkA58"
spreadsheet = client.open_by_key(spreadsheet_id)

print("🔍 현재 문서에 포함된 시트 목록:")
for idx, sheet in enumerate(spreadsheet.worksheets()):
    print(f"  [{idx}] {sheet.title}")

worksheet = spreadsheet.get_worksheet(2)
print("\n✅ 선택된 시트:", worksheet.title)

try:
    records = worksheet.get_all_records()
    df = pd.DataFrame(records)
    # 오류 제거
    df = df[~df['통계시도명'].astype(str).str.contains('#REF!')]
    # 주소 결합
    df["full_address"] = df["통계시도명"] + " " + df["통계시군구명"]
    # 주소 열 생성
    df[['lat', 'lon']] = df['full_address'].apply(get_coords)

    # 시군구별 전체 지급건수
    total_by_region = df.groupby(['통계시도명', '통계시군구명', 'lat', 'lon'])['지급건수'].sum().reset_index()

    # 지도 초기화
    fig = go.Figure()

    # 1. 버블 (시군구 위치에 따라 지급건수 크기)
    fig.add_trace(go.Scattergeo(
        lon = total_by_region['lon'],
        lat = total_by_region['lat'],
        text = total_by_region['통계시군구명'] + "<br>지급건수: " + total_by_region['지급건수'].astype(str),
        marker = dict(
            size = (total_by_region['지급건수'] / 50).tolist(),  # 크기 조절
            color = 'skyblue',
            line_color='darkblue',
            line_width=1,
            sizemode = 'area',
            opacity=0.6
        ),
        hoverinfo = 'text',
        name = '지급건수 버블'
    ))

    # 2. 파이차트 (각 시군구에 pie를 하나씩 그려줌)
    for (region, lat, lon), group in df.groupby(['통계시군구명', 'lat', 'lon']):
        fig.add_trace(go.Pie(
            labels=group['지원구분'],
            values=group['지급건수'],
            name=region,
            domain=dict(x=[0,0.1], y=[0,0.1]),  # 위치는 아래에서 직접 지정
            textinfo='percent+label',
            hoverinfo='label+value',
            showlegend=False,
            hole=0.3
        ))
        # 위치 강제 조절 (파이 위치를 지도에 맞춰야 하므로 추후 manual layout 필요)

    # 3. 지도 설정
    fig.update_layout(
        title="지자체별 아동양육 관련 지원 현황",
        geo=dict(
            scope='asia',
            projection_type='mercator',
            showland=True,
            landcolor="rgb(243, 243, 243)",
            showcountries=True,
            center=dict(lat=36.5, lon=127.8),
            resolution=50,
            lataxis_range=[33, 39],
            lonaxis_range=[125, 130]
        ),
        height=700
    )

    fig.show()
    
except gspread.exceptions.GSpreadException as e:
    print("❌ 실패했습니다:", str(e))
