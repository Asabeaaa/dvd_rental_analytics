import os
import pandas as pd
from sqlalchemy import create_engine
from settings import settings
from helper import load_tables

BASE_DIR = os.path.dirname(os.path.abspath("__file__"))

POSTGRESQL_ENGINE = create_engine(
    f"postgresql+psycopg2://{settings.DB_USER}:{settings.DB_PASSWORD}@{settings.DB_HOST}:5432/{settings.DB_NAME}"
)

EXPORT_TABLES_DIR = os.path.join(BASE_DIR, "exports", "merges")
os.makedirs(EXPORT_TABLES_DIR, exist_ok=True)


"""
Datasets and join justifications:

1. category_revenue — which categories generate the most revenue
   - payment and rental: INNER JOIN on rental_id — only payments tied to a rental
   - rental and inventory: INNER JOIN on inventory_id — rentals reference an inventory
   - inventory and film_category: INNER JOIN on film_id — inventory references a film
   - film_category and category: INNER JOIN on category_id — use category id to get it's name

2. category_rental_volume — which categories are rented the most, to compare against revenue
   - rental and inventory: INNER JOIN on inventory_id — rentals reference an inventory
   - inventory and film_category: INNER JOIN on film_id — inventory references a film
   - film_category and category: INNER JOIN on category_id — use category id to get it's name

3. store_performance — which store generates more revenue
   - payment and rental: INNER JOIN on rental_id — only payments tied to a rental
   - rental and inventory: INNER JOIN on inventory_id — inventory tells us which store

4. store_category_mix — which categories drive rentals at each store, to check if the top category 
                        at the weaker store is actually stronger than at the better performing store
   - rental and inventory: INNER JOIN on inventory_id — inventory carries both film_id and store_id
   - inventory and film_category: INNER JOIN on film_id — resolve film to category
   - film_category and category: INNER JOIN on category_id — resolve category id to name


Assumptions:
   - payment is the source of truth for revenue — rentals with no payment row are excluded
     from revenue datasets but included in volume datasets
   - inventory carries store_id — this is how rentals are attributed to a store, not the
     staff member who processed it
   - film_category is a many-to-one relationship in this dataset — each film belongs to
     exactly one category, so joining through film_category does not expand rows
   - category_revenue and category_rental_volume are built independently rather than
     derived from one another — revenue excludes unpaid rentals, volume does not, so
     they are intentionally not comparable row-for-row
   - store_category_mix is at rental grain — to compare categories across stores you
     must aggregate by store_id and category before drawing conclusions


Limitations:
   - store_performance only reflects recorded payments, not total rental activity
   - category_revenue and category_rental_volume may rank differently because a high-volume
    category may have a lower rental_rate, making it weaker on revenue
"""


def build_category_revenue(dataframes: dict) -> pd.DataFrame:
    payment = dataframes["payment"]
    rental = dataframes["rental"]
    inventory = dataframes["inventory"]
    film_category = dataframes["film_category"]
    category = dataframes["category"]

    df = payment.merge(
        rental[["rental_id", "inventory_id"]],
        on="rental_id", how="inner"
    ).merge(
        inventory[["inventory_id", "film_id"]],
        on="inventory_id", how="inner"
    ).merge(
        film_category[["film_id", "category_id"]],
        on="film_id", how="inner"
    ).merge(
        category[["category_id", "name"]].rename(columns={"name": "category"}),
        on="category_id", how="inner"
    )

    return df


def build_category_rental_volume(dataframes: dict) -> pd.DataFrame:
    rental = dataframes["rental"]
    inventory = dataframes["inventory"]
    film_category = dataframes["film_category"]
    category = dataframes["category"]

    df = rental.merge(
        inventory[["inventory_id", "film_id"]],
        on="inventory_id", how="inner"
    ).merge(
        film_category[["film_id", "category_id"]],
        on="film_id", how="inner"
    ).merge(
        category[["category_id", "name"]].rename(columns={"name": "category"}),
        on="category_id", how="inner"
    )

    return df


def build_store_performance(dataframes: dict) -> pd.DataFrame:
    payment = dataframes["payment"]
    rental = dataframes["rental"]
    inventory = dataframes["inventory"]

    df = payment.merge(
        rental[["rental_id", "inventory_id"]],
        on="rental_id", how="inner"
    ).merge(
        inventory[["inventory_id", "store_id"]],
        on="inventory_id", how="inner"
    )

    return df


def build_store_category_mix(dataframes: dict) -> pd.DataFrame:
    rental = dataframes["rental"]
    inventory = dataframes["inventory"]
    film_category = dataframes["film_category"]
    category = dataframes["category"]

    df = rental.merge(
        inventory[["inventory_id", "film_id", "store_id"]],
        on="inventory_id", how="inner"
    ).merge(
        film_category[["film_id", "category_id"]],
        on="film_id", how="inner"
    ).merge(
        category[["category_id", "name"]].rename(columns={"name": "category"}),
        on="category_id", how="inner"
    )

    return df


def validate_merge(name: str, original: pd.Series, merged: pd.DataFrame, join_key: str) -> None:
    print(f"\n{name}:")
    print(f"  original {join_key} unique: {original[join_key].nunique()}")
    print(f"  merged rows: {len(merged)}")
    print(f"  merged {join_key} unique: {merged[join_key].nunique()}")
    nulls = merged.isnull().sum()
    nulls = nulls[nulls > 0]
    print(f"  null counts:\n{nulls if not nulls.empty else '  none'}")


if __name__ == "__main__":
    dataframes = load_tables(POSTGRESQL_ENGINE)

    category_revenue = build_category_revenue(dataframes)
    category_rental_volume = build_category_rental_volume(dataframes)
    store_performance = build_store_performance(dataframes)
    store_category_mix = build_store_category_mix(dataframes)

    validate_merge("category_revenue",
                   dataframes["payment"], category_revenue, "rental_id")
    validate_merge("category_rental_volume",
                   dataframes["rental"], category_rental_volume, "rental_id")
    validate_merge("store_performance",
                   dataframes["payment"], store_performance, "rental_id")
    validate_merge("store_category_mix",
                   dataframes["rental"], store_category_mix, "rental_id")

    category_revenue.to_csv(os.path.join(
        EXPORT_TABLES_DIR, "category_revenue.csv"), index=False)
    category_rental_volume.to_csv(os.path.join(
        EXPORT_TABLES_DIR, "category_rental_volume.csv"), index=False)
    store_performance.to_csv(os.path.join(
        EXPORT_TABLES_DIR, "store_performance.csv"), index=False)
    store_category_mix.to_csv(os.path.join(
        EXPORT_TABLES_DIR, "store_category_mix.csv"), index=False)

    POSTGRESQL_ENGINE.dispose()
