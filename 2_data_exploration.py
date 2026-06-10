import os
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from sqlalchemy import create_engine
from settings import settings
from helper import load_tables

POSTGRESQL_ENGINE = create_engine(
    f"postgresql+psycopg2://{settings.DB_USER}:{settings.DB_PASSWORD}@{settings.DB_HOST}:5432/{settings.DB_NAME}"
)


BASE_DIR = os.path.dirname(os.path.abspath("__file__"))

EXPORT_VIZ_DIR = os.path.join(BASE_DIR, "exports", "results")
EXPORT_TABLES_DIR = os.path.join(BASE_DIR, "exports", "tables")
os.makedirs(EXPORT_VIZ_DIR, exist_ok=True)
os.makedirs(EXPORT_TABLES_DIR, exist_ok=True)

plt.style.use("seaborn-v0_8-whitegrid")
sns.set_palette("husl")


def inspect_schema(dataframes: dict) -> None:
    for table, df in dataframes.items():
        print(f"\n{table}:")
        df.info()


def missing_values(dataframes: dict) -> None:
    summary_rows = []

    for table, df in dataframes.items():
        missing = df.isnull().sum()
        missing = missing[missing > 0]
        print(f"\n{table}:")
        print(missing if not missing.empty else "no missing values")

        for column, count in missing.items():
            summary_rows.append({
                "table": table,
                "column": column,
                "missing_count": count
            })

    if summary_rows:
        pd.DataFrame(summary_rows).to_csv(
            os.path.join(EXPORT_TABLES_DIR, "missing_values.csv"), index=False)


def identify_outliers(dataframes: dict) -> None:
    checks = {
        "payment": "amount",
        "film": "rental_rate",
        "film": "replacement_cost"
    }

    summary_rows = []

    for table, column in checks.items():
        df = dataframes[table]
        q1 = df[column].quantile(0.25)
        q3 = df[column].quantile(0.75)
        iqr = q3 - q1
        lower = round(q1 - 1.5 * iqr, 2)
        upper = round(q3 + 1.5 * iqr, 2)

        above = df[df[column] > upper]
        below = df[df[column] < lower]

        print(f"\n{table}.{column} outliers:")
        print(f"  lower bound: {lower}, upper bound: {upper}")
        if not above.empty:
            print(above[[column]])
        if not below.empty:
            print(below[[column]])

        summary_rows.append({
            "table": table,
            "column": column,
            "lower_bound": lower,
            "upper_bound": upper,
            "count_above_upper": len(above),
            "count_below_lower": len(below),
        })

    pd.DataFrame(summary_rows).to_csv(
        os.path.join(EXPORT_TABLES_DIR, "outliers.csv"), index=False)


def descriptive_stats(dataframes: dict):
    for table, df in dataframes.items():
        print(f"\n{table}:")
        print(df.describe(include="all"))


def plot_rentals_by_month(dataframes: dict) -> None:
    df = dataframes["rental"].copy()
    df["month"] = pd.to_datetime(
        df["rental_date"]).dt.to_period("M").dt.to_timestamp()
    monthly = df.groupby("month").size().reset_index(name="rentals")

    fig, ax = plt.subplots(figsize=(12, 5))
    ax.plot(monthly["month"], monthly["rentals"], marker="o", linewidth=2)
    ax.set_title("Rental Volume by Month", fontsize=14, fontweight="bold")
    ax.set_xlabel("Month")
    ax.set_ylabel("Number of Rentals")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    plt.tight_layout()
    plt.savefig(os.path.join(EXPORT_VIZ_DIR, "rentals_by_month.png"),
                dpi=150, bbox_inches="tight")
    plt.close()


def plot_payment_distribution(dataframes: dict) -> None:
    df = dataframes["payment"]

    fig, ax = plt.subplots(figsize=(10, 5))
    sns.histplot(df["amount"], bins=30, kde=True, ax=ax)
    ax.set_title("Payment Amount Distribution", fontsize=14, fontweight="bold")
    ax.set_xlabel("Amount")
    ax.set_ylabel("Frequency")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    plt.tight_layout()
    plt.savefig(os.path.join(EXPORT_VIZ_DIR, "payment_distribution.png"),
                dpi=150, bbox_inches="tight")
    plt.close()


def plot_top_customers(dataframes: dict) -> None:
    payments = dataframes["payment"]
    customers = dataframes["customer"]

    df = payments.groupby("customer_id")[
        "amount"].sum().reset_index(name="total_spent")
    df = df.merge(
        customers[["customer_id", "first_name", "last_name"]], on="customer_id")
    df["customer"] = df["first_name"] + " " + df["last_name"]
    df = df.nlargest(15, "total_spent")

    fig, ax = plt.subplots(figsize=(12, 6))
    sns.barplot(data=df, x="total_spent", y="customer", ax=ax)
    ax.set_title("Top 15 Customers by Total Spend",
                 fontsize=14, fontweight="bold")
    ax.set_xlabel("Total Spent")
    ax.set_ylabel("Customer")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    plt.tight_layout()
    plt.savefig(os.path.join(EXPORT_VIZ_DIR, "top_customers.png"),
                dpi=150, bbox_inches="tight")
    plt.close()


def plot_rentals_by_day_of_week(dataframes: dict) -> None:
    df = dataframes["rental"].copy()
    df["day_of_week"] = pd.to_datetime(df["rental_date"]).dt.day_name()

    ordered_days = ["Monday", "Tuesday", "Wednesday",
                    "Thursday", "Friday", "Saturday", "Sunday"]
    day_counts = df["day_of_week"].value_counts().reindex(
        ordered_days).reset_index()
    day_counts.columns = ["day_of_week", "rentals"]

    fig, ax = plt.subplots(figsize=(10, 5))
    sns.barplot(data=day_counts, x="day_of_week", y="rentals", ax=ax)
    ax.set_title("Rental Volume by Day of Week",
                 fontsize=14, fontweight="bold")
    ax.set_xlabel("Day")
    ax.set_ylabel("Number of Rentals")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    plt.tight_layout()
    plt.savefig(os.path.join(EXPORT_VIZ_DIR, "rentals_by_day_of_week.png"),
                dpi=150, bbox_inches="tight")
    plt.close()


def plot_top_rented_films(dataframes: dict) -> None:
    rental = dataframes["rental"]
    inventory = dataframes["inventory"]
    film = dataframes["film"]

    df = rental.merge(
        inventory[["inventory_id", "film_id"]], on="inventory_id", how="inner")
    df = df.merge(film[["film_id", "title"]], on="film_id", how="inner")
    df = df.groupby("title").size().reset_index(
        name="rental_count").nlargest(15, "rental_count")

    fig, ax = plt.subplots(figsize=(12, 6))
    sns.barplot(data=df, x="rental_count", y="title", ax=ax)
    ax.set_title("Top 15 Most Rented Films", fontsize=14, fontweight="bold")
    ax.set_xlabel("Number of Rentals")
    ax.set_ylabel("Film")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    plt.tight_layout()
    plt.savefig(os.path.join(EXPORT_VIZ_DIR, "top_rented_films.png"),
                dpi=150, bbox_inches="tight")
    plt.close()


if __name__ == "__main__":
    dataframes = load_tables(POSTGRESQL_ENGINE)

    inspect_schema(dataframes)
    missing_values(dataframes)
    identify_outliers(dataframes)
    descriptive_stats(dataframes)

    # plots
    plot_rentals_by_month(dataframes)
    plot_rentals_by_day_of_week(dataframes)
    plot_payment_distribution(dataframes)
    plot_top_customers(dataframes)
    plot_top_rented_films(dataframes)

    # close connection pool
    POSTGRESQL_ENGINE.dispose()
