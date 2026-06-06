import os
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

BASE_DIR = os.path.dirname(os.path.abspath("__file__"))
load_dotenv(os.path.join(BASE_DIR, ".env"))

DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_NAME = os.getenv("DB_NAME_DVD")

POSTGRESQL_ENGINE = create_engine(
    f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:5432/{DB_NAME}"
)

EXPORT_VIZ_DIR = os.path.join(BASE_DIR, "exports", "results")
EXPORT_TABLES_DIR = os.path.join(BASE_DIR, "exports", "tables")
os.makedirs(EXPORT_VIZ_DIR, exist_ok=True)
os.makedirs(EXPORT_TABLES_DIR, exist_ok=True)

plt.style.use("seaborn-v0_8-whitegrid")
sns.set_palette("husl")

TABLES = ["film", "actor", "customer", "rental",
          "payment", "inventory", "store", "staff"]


def load_tables():
    dataframes = {}
    with POSTGRESQL_ENGINE.begin() as conn:
        for table in TABLES:
            dataframes[table] = pd.read_sql(
                text(f"SELECT * FROM {table};"), conn)
    return dataframes


def inspect_schema(dataframes):
    for table, df in dataframes.items():
        print(f"\n{table}:")
        df.info()


def descriptive_stats(dataframes):
    for table, df in dataframes.items():
        print(f"\n{table}:")
        print(df.describe(include="all"))


def missing_values(dataframes):
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
                "missing_count": count,
                "missing_pct": round(count / len(df) * 100, 2)
            })

    if summary_rows:
        pd.DataFrame(summary_rows).to_csv(
            os.path.join(EXPORT_TABLES_DIR, "missing_values.csv"), index=False)


def identify_outliers(dataframes):
    df = dataframes["payment"]
    q1 = df["amount"].quantile(0.25)
    q3 = df["amount"].quantile(0.75)
    iqr = q3 - q1
    outliers = df[(df["amount"] < q1 - 1.5 * iqr) |
                  (df["amount"] > q3 + 1.5 * iqr)].copy()

    print(f"\npayment outliers (IQR method): {len(outliers)} rows")
    print(outliers["amount"].describe())

    outliers.to_csv(
        os.path.join(EXPORT_TABLES_DIR, "outliers.csv"), index=False)


def plot_rentals_by_month(dataframes):
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


def plot_payment_distribution(dataframes):
    df = dataframes["payment"]

    fig, ax = plt.subplots(figsize=(10, 5))
    sns.histplot(df["amount"], bins=30, kde=True, ax=ax)
    ax.set_title("Payment Amount Distribution", fontsize=14, fontweight="bold")
    ax.set_xlabel("Amount ($)")
    ax.set_ylabel("Frequency")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    plt.tight_layout()
    plt.savefig(os.path.join(EXPORT_VIZ_DIR, "payment_distribution.png"),
                dpi=150, bbox_inches="tight")
    plt.close()


def plot_top_customers(dataframes):
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
    ax.set_xlabel("Total Spent ($)")
    ax.set_ylabel("Customer")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    plt.tight_layout()
    plt.savefig(os.path.join(EXPORT_VIZ_DIR, "top_customers.png"),
                dpi=150, bbox_inches="tight")
    plt.close()


def plot_film_rating_distribution(dataframes):
    df = dataframes["film"]

    fig, ax = plt.subplots(figsize=(10, 5))
    rating_counts = df["rating"].value_counts().reset_index()
    sns.barplot(data=rating_counts, x="rating", y="count", ax=ax)
    ax.set_title("Film Count by Rating", fontsize=14, fontweight="bold")
    ax.set_xlabel("Rating")
    ax.set_ylabel("Count")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    plt.tight_layout()
    plt.savefig(os.path.join(EXPORT_VIZ_DIR, "film_rating_distribution.png"),
                dpi=150, bbox_inches="tight")
    plt.close()


if __name__ == "__main__":
    dataframes = load_tables()

    inspect_schema(dataframes)
    descriptive_stats(dataframes)
    missing_values(dataframes)
    identify_outliers(dataframes)

    plot_rentals_by_month(dataframes)
    plot_payment_distribution(dataframes)
    plot_top_customers(dataframes)
    plot_film_rating_distribution(dataframes)

    POSTGRESQL_ENGINE.dispose()
