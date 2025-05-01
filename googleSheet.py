import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials

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

worksheet = spreadsheet.get_worksheet(0)
print("\n✅ 선택된 시트:", worksheet.title)

