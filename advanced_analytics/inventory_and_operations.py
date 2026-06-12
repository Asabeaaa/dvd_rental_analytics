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


def analyse_turnover(rental: pd.DataFrame, inventory: pd.DataFrame, film: pd.DataFrame) -> None:
    copies_per_film = inventory.groupby(
        "film_id").size().reset_index(name="copy_count")
    rentals_per_film = rental.merge(
        inventory[["inventory_id", "film_id"]], on="inventory_id", how="inner"
    ).groupby("film_id").size().reset_index(name="rental_count")

    df = copies_per_film.merge(rentals_per_film, on="film_id", how="left")
    df["rental_count"] = df["rental_count"].fillna(0)
    df["turnover_rate"] = (df["rental_count"] / df["copy_count"]).round(4)

    df = df.merge(film[["film_id", "title"]], on="film_id", how="inner")

    top_10 = df.nlargest(10, "turnover_rate")[
        ["title", "copy_count", "rental_count", "turnover_rate"]
    ]

    print("\nTop 10 Films by Turnover Rate:")
    print(top_10.to_string(index=False))
    top_10.to_csv(os.path.join(EXPORT_TABLES_DIR,
                  "film_turnover.csv"), index=False)

    fig, ax = plt.subplots(figsize=(12, 6))
    sns.barplot(data=top_10, x="turnover_rate", y="title", ax=ax)
    ax.set_title("Top 10 Films by Turnover Rate",
                 fontsize=14, fontweight="bold")
    ax.set_xlabel("Turnover Rate")
    ax.set_ylabel("Film")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    plt.tight_layout()
    plt.savefig(os.path.join(EXPORT_VIZ_DIR, "film_turnover.png"),
                dpi=150, bbox_inches="tight")
    plt.close()


def analyse_store_comparison(store_performance: pd.DataFrame, store_category_mix: pd.DataFrame) -> None:
    rental_by_store = store_category_mix.groupby(
        "store_id").size().reset_index(name="rental_count")
    rental_by_store["store_id"] = rental_by_store["store_id"].astype(str)

    top_category_per_store = (
        store_category_mix.groupby(
            ["store_id", "category"]).size().reset_index(name="rental_count")
        .sort_values(["store_id", "rental_count"], ascending=[True, False])
        .groupby("store_id").head(5)
        .reset_index(drop=True)
    )
    top_category_per_store["store_id"] = top_category_per_store["store_id"].astype(
        str)

    print("\nStore Rental Volume:")
    print(rental_by_store.to_string(index=False))
    print("\nTop 5 Categories per Store:")
    print(top_category_per_store.to_string(index=False))

    rental_by_store.to_csv(os.path.join(
        EXPORT_TABLES_DIR, "store_comparison.csv"), index=False)
    top_category_per_store.to_csv(os.path.join(
        EXPORT_TABLES_DIR, "store_category_mix.csv"), index=False)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))

    sns.barplot(data=rental_by_store, x="store_id", y="rental_count", ax=ax1)
    ax1.set_title("Rental Volume by Store", fontsize=14, fontweight="bold")
    ax1.set_xlabel("Store")
    ax1.set_ylabel("Rental Count")
    ax1.spines["top"].set_visible(False)
    ax1.spines["right"].set_visible(False)

    stores = top_category_per_store["store_id"].unique()
    width = 0.35
    categories = top_category_per_store[
        top_category_per_store["store_id"] == stores[0]]["category"].tolist()
    x = range(len(categories))

    for i, store in enumerate(stores):
        store_df = top_category_per_store[top_category_per_store["store_id"] == store]
        ax2.bar([j + i * width for j in x], store_df["rental_count"],
                width, label=f"Store {store}")

    ax2.set_xticks([j + width / 2 for j in x])
    ax2.set_xticklabels(categories, rotation=45, ha="right")
    ax2.set_title("Top 5 Categories per Store", fontsize=14, fontweight="bold")
    ax2.set_xlabel("Category")
    ax2.set_ylabel("Rental Count")
    ax2.legend()
    ax2.spines["top"].set_visible(False)
    ax2.spines["right"].set_visible(False)

    plt.tight_layout()
    plt.savefig(os.path.join(EXPORT_VIZ_DIR, "store_comparison.png"),
                dpi=150, bbox_inches="tight")
    plt.close()


def analyse_stock_efficiency(rental: pd.DataFrame, inventory: pd.DataFrame, film: pd.DataFrame) -> None:
    copies_per_film = inventory.groupby(
        "film_id").size().reset_index(name="copy_count")
    rentals_per_film = rental.merge(
        inventory[["inventory_id", "film_id"]], on="inventory_id", how="inner"
    ).groupby("film_id").size().reset_index(name="rental_count")

    df = copies_per_film.merge(rentals_per_film, on="film_id", how="left")
    df["rental_count"] = df["rental_count"].fillna(0)
    df["rentals_per_copy"] = (df["rental_count"] / df["copy_count"]).round(4)

    df = df.merge(film[["film_id", "title"]], on="film_id", how="inner")

    overstocked = df[df["rentals_per_copy"] < df["rentals_per_copy"].quantile(0.25)].nlargest(
        10, "copy_count")[["title", "copy_count", "rental_count", "rentals_per_copy"]]

    understocked = df[df["rentals_per_copy"] > df["rentals_per_copy"].quantile(0.75)].nsmallest(
        10, "copy_count")[["title", "copy_count", "rental_count", "rentals_per_copy"]]

    print("\nOverstocked Films (most copies, least rented):")
    print(overstocked.to_string(index=False))

    print("\nUnderstocked Films (fewest copies, most rented):")
    print(understocked.to_string(index=False))

    overstocked.to_csv(os.path.join(EXPORT_TABLES_DIR,
                       "overstocked_films.csv"), index=False)
    understocked.to_csv(os.path.join(EXPORT_TABLES_DIR,
                        "understocked_films.csv"), index=False)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))

    sns.barplot(data=overstocked, x="copy_count", y="title", ax=ax1)
    ax1.set_title("Overstocked Films", fontsize=14, fontweight="bold")
    ax1.set_xlabel("Copy Count")
    ax1.set_ylabel("Film")
    ax1.spines["top"].set_visible(False)
    ax1.spines["right"].set_visible(False)

    sns.barplot(data=understocked, x="rentals_per_copy", y="title", ax=ax2)
    ax2.set_title("Understocked Films", fontsize=14, fontweight="bold")
    ax2.set_xlabel("Rentals per Copy")
    ax2.set_ylabel("Film")
    ax2.spines["top"].set_visible(False)
    ax2.spines["right"].set_visible(False)

    plt.tight_layout()
    plt.savefig(os.path.join(EXPORT_VIZ_DIR, "stock_efficiency.png"),
                dpi=150, bbox_inches="tight")
    plt.close()
