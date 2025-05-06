import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd



# API 키 인증        
script_dir = os.path.dirname(os.path.abspath(__file__))
key_path = os.path.join(script_dir, "../key/datascience-457408-eb15d8611be3.json")
if not os.path.exists(key_path):
    raise FileNotFoundError(f"키 파일을 찾을 수 없습니다: {key_path}")
creds = ServiceAccountCredentials.from_json_keyfile_name(key_path, scopes=[
            "https://www.googleapis.com/auth/spreadsheets.readonly",
            "https://www.googleapis.com/auth/drive.readonly",
        ],)
client = gspread.authorize(creds)

# 시트 가져오기
spreadsheet_id = "1_m5GzATyDfHQ6GH_AIDt96dG-fUkLt-I4a93XlSkA58"
spreadsheet = client.open_by_key(spreadsheet_id)

print("🔍 현재 문서에 포함된 시트 목록:")
for idx, sheet in enumerate(spreadsheet.worksheets()):
    print(f"  [{idx}] {sheet.title}")

worksheet = spreadsheet.get_worksheet(3) # 원하는 시트 번호 입력
print("\n✅ 선택된 시트:", worksheet.title)

try:
    records = worksheet.get_all_records()
    df = pd.DataFrame(records)
    print(df)
    
except gspread.exceptions.GSpreadException as e:
    print("❌ 실패했습니다:", str(e))
