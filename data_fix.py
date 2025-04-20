import pandas as pd

# CSV 불러오기
df = pd.read_csv("./한부모가족 지원구분별 지급건수.csv", encoding="utf-8")

# 열 분리 처리
blocks = []
for i in range(0, 5):  # 5개월치
    suffix = "" if i == 0 else f".{i}"
    cols = [f"통계연월{suffix}", f"통계시도명{suffix}", f"통계시군구명{suffix}", f"지원구분{suffix}", f"지급건수{suffix}"]
    if all(c in df.columns for c in cols):
        temp = df[cols].copy()
        temp.columns = ["통계연월", "통계시도명", "통계시군구명", "지원구분", "지급건수"]

        # 지급건수를 숫자로 강제 변환
        temp["지급건수"] = pd.to_numeric(temp["지급건수"], errors="coerce")
        blocks.append(temp)

# 하나로 합치기
merged = pd.concat(blocks, ignore_index=True)

# 통합 월만 필터
months_to_sum = ["202503", "202502", "202501", "202412"]
filtered = merged[merged["통계연월"].isin(months_to_sum)]

# 지급건수 그룹별 합산
summed = (
    filtered.groupby(["통계시도명", "통계시군구명", "지원구분"], as_index=False)
    .agg({"지급건수": "sum"})
)
summed["통계연월"] = "통합"

# 열 순서 맞추기
summed = summed[["통계연월", "통계시도명", "통계시군구명", "지원구분", "지급건수"]]

# 기존 데이터에 통합 행 추가
final_df = pd.concat([merged, summed], ignore_index=True)

# 저장
final_df.to_csv("output.csv", index=False, encoding="utf-8-sig")

# 확인
print(final_df[final_df["통계연월"] == "통합"])
