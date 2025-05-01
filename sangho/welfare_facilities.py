import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import matplotlib
from geopy.geocoders import Nominatim
import time
import folium
import numpy as np
import re

# 지오코더 설정
geolocator = Nominatim(user_agent="welfare-map", timeout=10)

# 주소 형식 정리
def clean_address(address):
    if pd.isna(address):
        return ""

    # 문자열로 캐스팅 후 기본 정리
    address = str(address).strip()

    # 완전히 주소가 아닌 경우 삭제
    if any(keyword in address for keyword in ["비공개", "작성자", "미혼모자", "안내"]):
        return ""

    # 괄호/인용 부호/이상한 문자 제거
    address = re.sub(r'[\(\)\[\]「」|※★·●◎▶▷◆◇□■○]', '', address)
    
    # 콤마 뒤 지우기
    address = re.sub(r',.*$', '', address)
    
    # "A동 B호", "202호", "한남하우스" 등 건물/호실 제거 (가능한 한 뒤쪽만 제거)
    address = re.sub(r'\s+\d{1,3}동\b', '', address)
    address = re.sub(r'\s+\d{1,3}호\b', '', address)
    address = re.sub(r'\s+\d{1,3}(호|층|호실)\b', '', address)
    address = re.sub(r'\s+\d{1,3}(호|층)?\s+[가-힣]{2,}\b', '', address)  # 예: "501 한남하우스"

    # "숫자-숫자"가 나오면 그 뒤는 제거
    address = re.sub(r'(\d+-\d+).*', r'\1', address)
    # 공백 정리
    address = re.sub(r'\s+', ' ', address).strip()

    return address



# 주소 → 위도/경도  
def geocode_address(address):
    address = clean_address(address) # 주소 전처리
    if not address or pd.isna(address):
        return pd.Series([None, None])
    try:
        time.sleep(0.5)
        location = geolocator.geocode(address)
        if location:
            print(f"주소 찾음: {address}")
            return pd.Series([location.latitude, location.longitude])
        else:
            print(f"⚠️ 주소를 찾을 수 없음: {address}")
            return pd.Series([None, None])
    except Exception as e:
        print(f"❌ 오류 발생 - 주소: {address} → {e}")
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

worksheet = spreadsheet.get_worksheet(1)
print("\n✅ 선택된 시트:", worksheet.title)

try:
    records = worksheet.get_all_records()
    df = pd.DataFrame(records)
    df.replace('', np.nan, inplace=True)
    df[['lat', 'lon']] = df['소재지'].apply(geocode_address)
    # 지도 기본 위치 (서울시청 기준)
    map_center = [37.5665, 126.9780]
    welfare_map = folium.Map(location=map_center, zoom_start=11)

    # 마커 추가
    for _, row in df.iterrows():
        if pd.notnull(row['lat']) and pd.notnull(row['lon']):
            folium.Marker(
                location=[row['lat'], row['lon']],
                popup=row.get('시설명', '이름 없음'),
                icon=folium.Icon(color='blue', icon='info-sign')
            ).add_to(welfare_map)

    # 지도 저장
    welfare_map.save("welfare_map.html")
except gspread.exceptions.GSpreadException as e:
    print("❌ 값을 가져오는 데 실패했습니다:", str(e))