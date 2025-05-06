    pca = PCA(n_components=2)
    df[['PC1','PC2']] = pca.fit_transform(df[norm_cols])

    # 이제 PC1, PC2가 생겼으니 공백 상위5 다시 뽑기
    top5 = df.nlargest(5, 'gap_diff')

    plt.figure(figsize=(6,5))
    plt.scatter(df['PC1'], df['PC2'], alpha=0.6)
    for _, row in top5.iterrows():
        plt.text(row['PC1'], row['PC2'], row['시도'], fontproperties=font_prop)