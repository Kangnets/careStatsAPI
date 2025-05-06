# -*- coding: utf-8 -*-
import os
import sys
import json
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib import font_manager
import gspread
from google.oauth2 import service_account

def setup_encoding_and_font():
    # 터미널 UTF-8 출력, 한글 폰트 설정
    sys.stdout.reconfigure(encoding='utf-8')
    script_dir = os.path.dirname(os.path.abspath(__file__))
    font_path  = os.path.join(script_dir, "Pretendard.ttf")
    if not os.path.exists(font_path):
        raise FileNotFoundError(f"폰트 파일을 찾을 수 없습니다: {font_path}")
    prop = font_manager.FontProperties(fname=font_path)
    plt.rc('font', family=prop.get_name())
    plt.rcParams['axes.unicode_minus'] = False

def calculate_city_income_sums(df):
    """
    '통계시도명', '중위소득비율구분', '수급자수' 컬럼을 이용해
    시도명×구간별 수급자수 합계를 pivot 형태로 반환.
    """
    df = df.copy()
    df.columns = df.columns.str.strip()
    df['통계시도명']       = df['통계시도명'].astype(str).str.strip()
    df['중위소득비율구분'] = df['중위소득비율구분'].astype(str).str.strip()
    df['수급자수']         = pd.to_numeric(df['수급자수'], errors='coerce').fillna(0).astype(int)

    grouped = df.groupby(
        ['통계시도명','중위소득비율구분'], as_index=False
    )['수급자수'].sum()
    pivot = grouped.pivot(
        index='통계시도명',
        columns='중위소득비율구분',
        values='수급자수'
    ).fillna(0)

    # 구간 순서 고정
    category_order = [
        "기타",
        "중위소득 30%이하",
        "중위소득 30~40%이하",
        "중위소득 40~50%이하",
        "중위소득 50~52%이하",
        "중위소득 52~60%이하",
        "중위소득 60~72%이하"
    ]
    pivot = pivot.reindex(columns=category_order, fill_value=0)
    return pivot

def main():
    setup_encoding_and_font()
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # 인증 및 시트 로드
    key_path = os.path.normpath(os.path.join(script_dir, "../key/datascience-457408-eb15d8611be3.json"))
    info     = json.load(open(key_path, encoding='utf-8'))
    info["private_key"] = info["private_key"].replace("\\n","\n")
    creds = service_account.Credentials.from_service_account_info(
        info,
        scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"],
    )
    client = gspread.authorize(creds)
    SPREADSHEET_ID = "1_m5GzATyDfHQ6GH_AIDt96dG-fUkLt-I4a93XlSkA58"
    ws = client.open_by_key(SPREADSHEET_ID).get_worksheet(3)

    # DataFrame 준비
    df = pd.DataFrame(ws.get_all_records())
    required = ['통계시도명','중위소득비율구분','수급자수']
    for col in required:
        if col not in df.columns:
            raise KeyError(f"'{col}' 컬럼이 없습니다.")
    df = df[required].dropna(subset=['통계시도명','중위소득비율구분'])

    # 1) 합계 계산 및 출력
    pivot = calculate_city_income_sums(df)
    print("=== 시도명 × 중위소득구간별 수급자수 합계 ===")
    print(pivot.to_string(), '\n')

    # 2) 각 도시별 도넛 차트 (범례로 수치+퍼센트)
    for city, row in pivot.iterrows():
        total = row.sum()
        if total == 0:
            print(f"{city}: 데이터 없음 (합계 0)\n")
            continue

        counts   = row
        percents = counts / total * 100

        fig, ax = plt.subplots(figsize=(10, 6))
        wedges, _ = ax.pie(
            counts,
            startangle=90,
            wedgeprops=dict(width=0.4, edgecolor='w')
        )

        # 범례 라벨에 수치와 퍼센트 함께 표시
        legend_labels = [
            f"{cat}: {counts[cat]}명 ({percents[cat]:.1f}%)"
            for cat in counts.index
        ]
        ax.legend(
            wedges,
            legend_labels,
            title="중위소득구간",
            loc='center left',
            bbox_to_anchor=(1, 0.5),
            fontsize=10,
            title_fontsize=12
        )

        ax.set_title(f"{city} 중위소득비율구간별 수급자 분포", pad=20)
        fig.subplots_adjust(right=0.75)  # 오른쪽 여백 확보
        plt.tight_layout()

        safe = city.replace(" ", "_").replace("/", "_")
        out_path = os.path.join(script_dir, f"{safe}_income_donut.png")
        plt.savefig(out_path, dpi=150)
        plt.close()
        print(f"{city} 도넛 차트 저장: {out_path}\n")

if __name__ == "__main__":
    main()
