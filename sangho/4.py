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
        
script_dir = os.path.dirname(os.path.abspath(__file__))
key_path = os.path.join(script_dir, "../datascience-457408-eb15d8611be3.json")
if not os.path.exists(key_path):
    raise FileNotFoundError(f"키 파일을 찾을 수 없습니다: {key_path}")
creds = ServiceAccountCredentials.from_json_keyfile_name(key_path, scopes=[
            "https://www.googleapis.com/auth/spreadsheets.readonly",
            "https://www.googleapis.com/auth/drive.readonly",
        ],)
client = gspread.authorize(creds)


spreadsheet_id = "1_m5GzATyDfHQ6GH_AIDt96dG-fUkLt-I4a93XlSkA58"
spreadsheet = client.open_by_key(spreadsheet_id)

print("🔍 현재 문서에 포함된 시트 목록:")
for idx, sheet in enumerate(spreadsheet.worksheets()):
    print(f"  [{idx}] {sheet.title}")

worksheet = spreadsheet.get_worksheet(4)
print("\n✅ 선택된 시트:", worksheet.title)

try:
    records = worksheet.get('A3:B23')
    df = pd.DataFrame(records)
    df = df.drop([0, 1, 2, 3])
    # df[1]을 숫자로 변환
    df[1] = pd.to_numeric(df[1], errors='coerce')  # 오류가 나면 NaN으로 변환
    print(df)
    
    # 각 시도에 대한 위도, 경도 추가
    df[['lat', 'lon']] = df[0].apply(get_coords)

    # 버블 차트 생성
    fig = go.Figure()

    fig.add_trace(go.Scattergeo(
        lon=df['lon'],
        lat=df['lat'],
        text=df[0] + "<br>한부모 가구 수: " + df[1].astype(str),
        marker=dict(
            size=df[1] / 1000,  # 가구 수에 비례한 버블 크기
            color='skyblue',
            line_color='darkblue',
            line_width=1,
            sizemode='area',
            opacity=0.6
        ),
        hoverinfo='text',
        name='한부모 가구'
    ))

    # 지도 설정
    fig.update_layout(
        title="각 지역별 한부모 가구 수",
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
