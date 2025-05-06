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
    sys.stdout.reconfigure(encoding='utf-8')
    script_dir = os.path.dirname(os.path.abspath(__file__))
    font_path  = os.path.join(script_dir, "Pretendard.ttf")
    if not os.path.exists(font_path):
        raise FileNotFoundError(f"폰트 파일을 찾을 수 없습니다: {font_path}")
    prop = font_manager.FontProperties(fname=font_path)
    plt.rc('font', family=prop.get_name())
    plt.rcParams['axes.unicode_minus'] = False

def calculate_city_family_sums(df):
    df = df.copy()
    df.columns = df.columns.str.strip()
    df['통계시도명'] = df['통계시도명'].astype(str).str.strip()
    df['가족유형']   = df['가족유형'].astype(str).str.strip()
    df['수급자수']   = pd.to_numeric(df['수급자수'], errors='coerce').fillna(0).astype(int)
    grouped = df.groupby(['통계시도명','가족유형'], as_index=False)['수급자수'].sum()
    pivot = grouped.pivot(index='통계시도명', columns='가족유형', values='수급자수').fillna(0)
    order = ['모자가족','부자가족','조손가족','청소년한부모모자가족','청소년한부모부자가족']
    return pivot.reindex(columns=order, fill_value=0)

def main():
    setup_encoding_and_font()
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # 인증
    key_path = os.path.normpath(os.path.join(script_dir, "../key/datascience-457408-eb15d8611be3.json"))
    info     = json.load(open(key_path, encoding='utf-8'))
    info['private_key'] = info['private_key'].replace('\\n','\n')
    creds = service_account.Credentials.from_service_account_info(
        info, scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
    )
    client = gspread.authorize(creds)

    # 데이터 로드
    ws = client.open_by_key("1_m5GzATyDfHQ6GH_AIDt96dG-fUkLt-I4a93XlSkA58").get_worksheet(3)
    df = pd.DataFrame(ws.get_all_records())[ ['통계시도명','가족유형','수급자수'] ].dropna()

    pivot = calculate_city_family_sums(df)

    for city, data in pivot.iterrows():
        total = data.sum()
        if total == 0:
            continue

        counts   = data
        percents = counts / total * 100

        # 도넛형 파이 차트, 넓은 가로 크기 지정
        fig, ax = plt.subplots(figsize=(12, 6))
        wedges, _ = ax.pie(
            counts,
            startangle=90,
            wedgeprops=dict(width=0.4, edgecolor='w')
        )
        # 범례 라벨에 수치 + 퍼센트
        legend_labels = [
            f"{cat}: {counts[cat]}명 ({percents[cat]:.1f}%)"
            for cat in counts.index
        ]
        ax.legend(
            wedges,
            legend_labels,
            title="가족유형",
            loc='center left',
            bbox_to_anchor=(1, 0.5),
            fontsize=10,
            title_fontsize=12
        )
        ax.set_title(f"{city} 가족유형별 수급자 분포", pad=20)

        # 레이아웃 조정: 오른쪽 여백 확보
        fig.subplots_adjust(right=0.75)

        out_png = os.path.join(script_dir, f"{city.replace(' ','_')}_family_type_pie.png")
        plt.savefig(out_png, dpi=150)
        plt.close()
        print(f"{city} 파이 차트 저장: {out_png}")

if __name__ == "__main__":
    main()
