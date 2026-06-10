import os
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns


BASE_DIR = os.path.dirname(os.path.abspath("__file__"))

EXPORT_TABLES_DIR = os.path.join(BASE_DIR, "exports", "tables")
EXPORT_VIZ_DIR = os.path.join(BASE_DIR, "exports", "visualizations")
EXPORT_MERGES_DIR = os.path.join(BASE_DIR, "exports", "merges")
os.makedirs(EXPORT_TABLES_DIR, exist_ok=True)
os.makedirs(EXPORT_VIZ_DIR, exist_ok=True)

plt.style.use("seaborn-v0_8-whitegrid")
sns.set_palette("husl")


def analyse_category_performance(category_revenue: pd.DataFrame, category_rental_volume: pd.DataFrame) -> None:
    revenue_by_category = category_revenue.groupby(
        "category")["amount"].sum().reset_index(name="total_revenue")
    payment_count_by_category = category_revenue.groupby(
        "category").size().reset_index(name="payment_count")
    volume_by_category = category_rental_volume.groupby(
        "category").size().reset_index(name="rental_count")

    df = revenue_by_category.merge(
        payment_count_by_category, on="category", how="inner")
    df = df.merge(volume_by_category, on="category", how="inner")
    df["revenue_per_rental"] = (
        df["total_revenue"] / df["rental_count"]).round(2)
    df["payment_rate"] = (
        df["payment_count"] / df["rental_count"]).round(2)
    df["revenue_rank"] = df["total_revenue"].rank(ascending=False).astype(int)
    df["volume_rank"] = df["rental_count"].rank(ascending=False).astype(int)
    df["rank_gap"] = df["volume_rank"] - df["revenue_rank"]

    df = df.sort_values("revenue_rank")

    print("\nCategory Performance:")
    print(df.to_string(index=False))
    df.to_csv(os.path.join(EXPORT_TABLES_DIR,
              "category_performance.csv"), index=False)

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))

    x = range(len(df))
    width = 0.35
    ax1_twin = ax1.twinx()
    ax1.bar([i - width/2 for i in x], df["total_revenue"],
            width, label="Total Revenue", color="steelblue")
    ax1_twin.bar([i + width/2 for i in x], df["rental_count"],
                 width, label="Rental Count", color="coral")
    ax1.set_xticks(list(x))
    ax1.set_xticklabels(df["category"], rotation=45, ha="right")
    ax1.set_title("Category Revenue vs Rental Volume",
                  fontsize=14, fontweight="bold")
    ax1.set_xlabel("Category")
    ax1.set_ylabel("Total Revenue")
    ax1_twin.set_ylabel("Rental Count")
    ax1.spines["top"].set_visible(False)
    ax1_twin.spines["top"].set_visible(False)
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax1_twin.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2)

    df_sorted = df.sort_values("payment_rate", ascending=False)
    x2 = range(len(df_sorted))
    ax2.bar(list(x2), df_sorted["payment_rate"], color="steelblue")
    ax2.set_xticks(list(x2))
    ax2.set_xticklabels(df_sorted["category"], rotation=45, ha="right")
    ax2.set_title("Payment Rate by Category", fontsize=14, fontweight="bold")
    ax2.set_xlabel("Category")
    ax2.set_ylabel("Payment Rate")
    ax2.spines["top"].set_visible(False)
    ax2.spines["right"].set_visible(False)

    plt.tight_layout()
    plt.savefig(os.path.join(EXPORT_VIZ_DIR,
                "category_performance.png"), dpi=150, bbox_inches="tight")
    plt.close()


def analyse_temporal_trends(category_rental_volume: pd.DataFrame) -> None:
    df = category_rental_volume.copy()
    df["rental_date"] = pd.to_datetime(df["rental_date"])
    df["month"] = df["rental_date"].dt.to_period("M").dt.to_timestamp()

    monthly_category = df.groupby(
        ["month", "category"]).size().reset_index(name="rental_count")

    top3_per_month = (
        monthly_category
        .sort_values(["month", "rental_count"], ascending=[True, False])
        .groupby("month")
        .head(3)
        .reset_index(drop=True)
    )

    print("\nTop 3 Categories by Month:")
    print(top3_per_month.to_string(index=False))
    top3_per_month.to_csv(os.path.join(EXPORT_TABLES_DIR,
                          "temporal_trends.csv"), index=False)

    fig, ax = plt.subplots(figsize=(14, 6))
    for category in top3_per_month["category"].unique():
        cat_df = top3_per_month[top3_per_month["category"] == category]
        ax.plot(cat_df["month"], cat_df["rental_count"],
                marker="o", linewidth=2, label=category)

    ax.set_title("Top 3 Categories by Rental Volume per Month",
                 fontsize=14, fontweight="bold")
    ax.set_xlabel("Month")
    ax.set_ylabel("Rental Count")
    ax.legend(loc="upper left", bbox_to_anchor=(1, 1))
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    plt.savefig(os.path.join(EXPORT_VIZ_DIR,
                "temporal_trends.png"), dpi=150, bbox_inches="tight")
    plt.close()


def analyse_pricing_insights(category_revenue: pd.DataFrame, category_rental_volume: pd.DataFrame) -> None:
    avg_payment = category_revenue.groupby(
        "category")["amount"].mean().reset_index(name="avg_payment")
    volume = category_rental_volume.groupby(
        "category").size().reset_index(name="rental_count")

    df = avg_payment.merge(volume, on="category", how="inner")
    df["volume_rank"] = df["rental_count"].rank(ascending=False).astype(int)
    df = df.sort_values("volume_rank")

    print("\nPricing Insights:")
    print(df.to_string(index=False))
    df.to_csv(os.path.join(EXPORT_TABLES_DIR,
              "pricing_insights.csv"), index=False)

    fig, ax1 = plt.subplots(figsize=(12, 6))
    ax2 = ax1.twinx()
    x = range(len(df))
    width = 0.35

    ax1.bar([i - width/2 for i in x], df["rental_count"],
            width, label="Rental Count", color="steelblue")
    ax2.bar([i + width/2 for i in x], df["avg_payment"],
            width, label="Avg Payment", color="coral")

    ax1.set_xticks(list(x))
    ax1.set_xticklabels(df["category"], rotation=45, ha="right")
    ax1.set_title("Rental Volume vs Average Payment by Category",
                  fontsize=14, fontweight="bold")
    ax1.set_xlabel("Category")
    ax1.set_ylabel("Rental Count")
    ax2.set_ylabel("Average Payment")
    ax1.spines["top"].set_visible(False)
    ax2.spines["top"].set_visible(False)
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2)

    plt.tight_layout()
    plt.savefig(os.path.join(EXPORT_VIZ_DIR,
                "pricing_insights.png"), dpi=150, bbox_inches="tight")
    plt.close()
