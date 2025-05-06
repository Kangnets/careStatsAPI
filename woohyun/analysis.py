# welfare_gap_analysis.py
# -*- coding: utf-8 -*-

import os
import json
import time
import pandas as pd
from sklearn.preprocessing import MinMaxScaler
from sklearn.decomposition import PCA
import gspread
from google.oauth2 import service_account
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from matplotlib import rc
from pandas.plotting import parallel_coordinates
import seaborn as sns

# 한글 폰트 설정
font_path = 'woohyun/Pretendard.ttf'  # 시스템 경로에 맞게 수정
font_prop = fm.FontProperties(fname=font_path)
rc('font', family=font_prop.get_name())
plt.rcParams['axes.unicode_minus'] = False

# 구글 스프레드시트 정보
SPREADSHEET_ID = "1_m5GzATyDfHQ6GH_AIDt96dG-fUkLt-I4a93XlSkA58"
KEY_REL_PATH = "../key/datascience-457408-eb15d8611be3.json"

# --- 데이터 로딩 함수 ---
def load_capacity():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    key_path = os.path.join(script_dir, KEY_REL_PATH)
    info = json.load(open(key_path, encoding='utf-8'))
    info['private_key'] = info['private_key'].replace('\\n', '\n')
    creds = service_account.Credentials.from_service_account_info(
        info,
        scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
    )
    client = gspread.authorize(creds)
    ws = client.open_by_key(SPREADSHEET_ID).get_worksheet(1)
    df = pd.DataFrame(ws.get_all_records())
    df.columns = df.columns.str.strip()
    df = df[['시도', '정원']].dropna(subset=['시도'])
    df['정원'] = pd.to_numeric(df['정원'], errors='coerce').fillna(0).astype(int)
    return (
        df.groupby('시도', as_index=False)['정원']
        .sum()
        .rename(columns={'정원': 'capacity'})
    )


def load_supports():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    key_path = os.path.join(script_dir, KEY_REL_PATH)
    info = json.load(open(key_path, encoding='utf-8'))
    info['private_key'] = info['private_key'].replace('\\n', '\n')
    creds = service_account.Credentials.from_service_account_info(
        info,
        scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
    )
    client = gspread.authorize(creds)
    ws = client.open_by_key(SPREADSHEET_ID).get_worksheet(2)
    df = pd.DataFrame(ws.get_all_records())
    df.columns = df.columns.str.strip()
    df = df[['통계시도명', '지급건수']].dropna(subset=['통계시도명'])
    df['지급건수'] = pd.to_numeric(df['지급건수'], errors='coerce').fillna(0).astype(int)
    return (
        df.groupby('통계시도명', as_index=False)['지급건수']
        .sum()
        .rename(columns={'통계시도명': '시도', '지급건수': 'support_count'})
    )


def load_households():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    key_path = os.path.join(script_dir, KEY_REL_PATH)
    creds = Credentials.from_service_account_file(
        key_path,
        scopes=[
            "https://www.googleapis.com/auth/spreadsheets.readonly",
            "https://www.googleapis.com/auth/drive.readonly"
        ]
    )
    client = gspread.authorize(creds)
    ws = client.open_by_key(SPREADSHEET_ID).get_worksheet(4)
    raw = ws.get('A3:B23')
    header = [c.strip() for c in raw[2]]
    rows = raw[4:]
    df = pd.DataFrame(rows, columns=header)
    df.columns = ['시도', 'household_count']
    df['시도'] = df['시도'].astype(str).str.strip()
    df['household_count'] = pd.to_numeric(df['household_count'], errors='coerce').fillna(0).astype(int)
    return df


def load_members():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    key_path = os.path.join(script_dir, KEY_REL_PATH)
    creds = Credentials.from_service_account_file(
        key_path,
        scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
    )
    service = build('sheets', 'v4', credentials=creds)
    meta = service.spreadsheets().get(spreadsheetId=SPREADSHEET_ID).execute()
    sheet_title = meta['sheets'][7]['properties']['title']
    resp = service.spreadsheets().values().get(
        spreadsheetId=SPREADSHEET_ID,
        range=f"{sheet_title}!A3:D"
    ).execute()
    vals = resp.get('values', [])
    header = [c.strip() for c in vals[0]]
    df = pd.DataFrame(vals[1:], columns=header)
    df.columns = ['시도', '특성1', '특성2', 'member_count']
    df = df[(df['특성1'] == '계') & (df['특성2'] == '소계') & (df['시도'] != '계')]
    df['member_count'] = df['member_count'].str.replace(',', '').astype(int)
    return df[['시도', 'member_count']]


def main():
    # 데이터 로드
    cap_df = load_capacity()
    sup_df = load_supports()
    hh_df = load_households()
    mem_df = load_members()

    # 병합 및 결측 처리
    df = (
        cap_df.merge(sup_df, on='시도', how='outer')
        .merge(hh_df, on='시도', how='outer')
        .merge(mem_df, on='시도', how='outer')
        .fillna(0)
    )

    # 정규화
    scaler = MinMaxScaler()
    raw_cols = ['capacity', 'support_count', 'household_count', 'member_count']
    norm_cols = [f"{c}_norm" for c in raw_cols]
    df[norm_cols] = scaler.fit_transform(df[raw_cols])

    # 상위 10개 선 그래프
    for col in norm_cols:
        top10 = df.nlargest(10, col)
        plt.figure()
        plt.plot(range(10), top10[col], marker='o', linestyle='-')
        plt.xticks(range(10), top10['시도'], rotation=90, fontproperties=font_prop)
        plt.title(f'{col} 상위 10개 지역', fontproperties=font_prop)
        plt.ylabel('정규화 값', fontproperties=font_prop)
        plt.tight_layout()
        plt.show()

    # 히스토그램: 원본 vs 정규화
    for raw, norm in zip(raw_cols, norm_cols):
        plt.figure(figsize=(8, 3))
        plt.subplot(1, 2, 1)
        plt.hist(df[raw], bins=15)
        plt.title(f'{raw} 원본 분포', fontproperties=font_prop)
        plt.subplot(1, 2, 2)
        plt.hist(df[norm], bins=15)
        plt.title(f'{norm} 정규화 분포', fontproperties=font_prop)
        plt.tight_layout()
        plt.show()

    # 공급·수요 지수 및 공백 계산
    df['supply_index'] = df[['capacity_norm', 'support_count_norm']].mean(axis=1)
    df['demand_index'] = df[['household_count_norm', 'member_count_norm']].mean(axis=1)
    df['gap_diff'] = df['demand_index'] - df['supply_index']
    df['gap_ratio'] = df['demand_index'] / (df['supply_index'] + 1e-6)

    # 상관관계 히트맵
    plt.figure(figsize=(6, 5))
    corr = df[norm_cols + ['supply_index', 'demand_index']].corr()
    sns.heatmap(corr, annot=True, fmt=".2f", cmap='Blues')
    plt.title('정규화 지표 및 지수 간 상관관계', fontproperties=font_prop)
    plt.tight_layout()
    plt.show()

    # 8) Parallel Coordinates: Top5 공백 지역 비교
    top5 = df.nlargest(5, 'gap_diff')
    pc_df = top5[['시도'] + norm_cols]
    plt.figure(figsize=(8, 4))
    parallel_coordinates(pc_df, '시도', color=sns.color_palette('Set2', 5))
    plt.title('Top5 공백 지역 정규화 지표 비교', fontproperties=font_prop)
    plt.ylabel('정규화 값', fontproperties=font_prop)
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.show()

    # 9) PCA 2D 투영  ← 이 주석과 동일한 들여쓰기 레벨로 아래 코드도 맞춥니다.
    pca = PCA(n_components=2)
    df[['PC1', 'PC2']] = pca.fit_transform(df[norm_cols])
    plt.figure(figsize=(6, 5))
    plt.scatter(df['PC1'], df['PC2'], alpha=0.6)
    for _, row in df.nlargest(5, 'gap_diff').iterrows():
        plt.text(row['PC1'], row['PC2'], row['시도'], fontproperties=font_prop)
    plt.axhline(0, color='gray', linewidth=0.5)
    plt.axvline(0, color='gray', linewidth=0.5)
    plt.title('정규화 지표 PCA 2D 투영', fontproperties=font_prop)
    plt.xlabel('PC1')
    plt.ylabel('PC2')
    plt.tight_layout()
    plt.show()

    # 10) 최종 결과 출력
    result = df.nlargest(10, 'gap_diff')
    print("\n=== 복지 공백 상위 10개 지역 ===")
    print(
        result.loc[:, ['시도'] + raw_cols + ['supply_index', 'demand_index', 'gap_diff', 'gap_ratio']].to_string(index=False)
    )

if __name__ == '__main__':
    main()