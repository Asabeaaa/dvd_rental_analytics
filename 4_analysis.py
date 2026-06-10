import os
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from sqlalchemy import create_engine
from settings import settings
from helper import load_tables

BASE_DIR = os.path.dirname(os.path.abspath("__file__"))

POSTGRESQL_ENGINE = create_engine(
    f"postgresql+psycopg2://{settings.DB_USER}:{settings.DB_PASSWORD}@{settings.DB_HOST}:5432/{settings.DB_NAME}"
)

EXPORT_TABLES_DIR = os.path.join(BASE_DIR, "exports", "tables")
EXPORT_VIZ_DIR = os.path.join(BASE_DIR, "exports", "visualizations")
os.makedirs(EXPORT_TABLES_DIR, exist_ok=True)
os.makedirs(EXPORT_VIZ_DIR, exist_ok=True)

plt.style.use("seaborn-v0_8-whitegrid")
sns.set_palette("husl")


def load_data():
    dataframes = load_tables(POSTGRESQL_ENGINE)
    return (
        dataframes["customer"],
        dataframes["rental"],
        dataframes["inventory"],
        dataframes["film_category"],
        dataframes["category"],
        dataframes["payment"]
    )


def analyse_segmentation(payment):
    df = payment.groupby("customer_id")["amount"].agg(
        total_spent="sum",
        payment_count="count"
    ).reset_index()

    df["segment"] = pd.qcut(df["total_spent"], q=3,
                            labels=["low", "mid", "high"])

    summary = df.groupby("segment")["total_spent"].agg(
        customer_count="count",
        avg_spend="mean",
        total_revenue="sum",
        min_spend="min",
        max_spend="max"
    ).reset_index()

    print("\nCustomer Segmentation:")
    print(summary.to_string(index=False))
    summary.to_csv(os.path.join(EXPORT_TABLES_DIR,
                   "customer_segments.csv"), index=False)

    fig, ax = plt.subplots(figsize=(10, 5))
    sns.barplot(data=summary, x="segment", y="total_revenue", ax=ax)
    ax.set_title("Total Revenue by Customer Segment",
                 fontsize=14, fontweight="bold")
    ax.set_xlabel("Segment")
    ax.set_ylabel("Total Revenue ($)")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    plt.tight_layout()
    plt.savefig(os.path.join(EXPORT_VIZ_DIR, "customer_segments.png"),
                dpi=150, bbox_inches="tight")
    plt.close()


def analyse_lifetime_value(customer, payment, rental):
    first_rental = rental.groupby("customer_id")[
        "rental_date"].min().reset_index()
    first_rental.columns = ["customer_id", "first_rental_date"]
    last_rental = rental.groupby("customer_id")[
        "rental_date"].max().reset_index()
    last_rental.columns = ["customer_id", "last_rental_date"]

    df = payment.groupby("customer_id")["amount"].agg(
        total_revenue="sum",
        total_purchases="count"
    ).reset_index()

    total_customers = df["customer_id"].nunique()
    purchase_frequency = df["total_purchases"].sum() / total_customers

    df["average_purchase_value"] = df["total_revenue"] / df["total_purchases"]
    df["purchase_frequency"] = purchase_frequency

    df = df.merge(first_rental, on="customer_id", how="left")
    df = df.merge(last_rental, on="customer_id", how="left")

    df["first_rental_date"] = pd.to_datetime(df["first_rental_date"])
    df["last_rental_date"] = pd.to_datetime(df["last_rental_date"])
    df["customer_lifespan"] = (
        (df["last_rental_date"] - df["first_rental_date"]).dt.days / 365).round(4)
    df["customer_lifespan"] = df["customer_lifespan"].replace(0, 1 / 365)

    df["clv"] = (df["average_purchase_value"] *
                 df["purchase_frequency"] * df["customer_lifespan"]).round(4)

    df = df.merge(
        customer[["customer_id", "first_name", "last_name"]],
        on="customer_id", how="inner"
    )
    df["customer_name"] = df["first_name"] + " " + df["last_name"]
    df = df.drop(columns=["first_name", "last_name"])

    top_10 = df.nlargest(10, "clv")[
        ["customer_name", "average_purchase_value",
            "purchase_frequency", "customer_lifespan", "clv"]
    ]

    print("\nCustomer Lifetime Value (top 10):")
    print(top_10.to_string(index=False))
    top_10.to_csv(os.path.join(EXPORT_TABLES_DIR,
                  "customer_ltv.csv"), index=False)

    fig, ax = plt.subplots(figsize=(10, 5))
    sns.histplot(df["clv"], bins=30, kde=True, ax=ax)
    ax.set_title("Customer Lifetime Value Distribution",
                 fontsize=14, fontweight="bold")
    ax.set_xlabel("CLV")
    ax.set_ylabel("Number of Customers")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    plt.tight_layout()
    plt.savefig(os.path.join(EXPORT_VIZ_DIR,
                "customer_ltv_distribution.png"), dpi=150, bbox_inches="tight")
    plt.close()


def analyse_churn_risk(customer, rental):
    last_rental = rental.groupby("customer_id")[
        "rental_date"].max().reset_index()
    last_rental.columns = ["customer_id", "last_rental_date"]

    snapshot_date = last_rental["last_rental_date"].max()

    last_rental["days_since_rental"] = (
        snapshot_date - last_rental["last_rental_date"]).dt.days

    last_rental["churn_risk"] = pd.cut(
        last_rental["days_since_rental"],
        bins=[-1, 30, 90, float("inf")],
        labels=["active", "at_risk", "churned"]
    )

    df = last_rental.merge(
        customer[["customer_id", "first_name", "last_name"]],
        on="customer_id", how="inner"
    )
    df["customer_name"] = df["first_name"] + " " + df["last_name"]
    df = df.drop(columns=["first_name", "last_name"])

    summary = df["churn_risk"].value_counts().reset_index()
    summary.columns = ["churn_risk", "customer_count"]

    print("\nChurn Risk:")
    print(summary.to_string(index=False))

    at_risk_churned = df[df["churn_risk"].isin(["at_risk", "churned"])]
    at_risk_churned.to_csv(os.path.join(
        EXPORT_TABLES_DIR, "customer_churn_risk.csv"), index=False)

    fig, ax = plt.subplots(figsize=(8, 5))
    sns.barplot(data=summary, x="churn_risk", y="customer_count", ax=ax)
    ax.set_title("Customer Churn Risk Distribution",
                 fontsize=14, fontweight="bold")
    ax.set_xlabel("Churn Risk")
    ax.set_ylabel("Number of Customers")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    plt.tight_layout()
    plt.savefig(os.path.join(EXPORT_VIZ_DIR, "customer_churn_risk.png"),
                dpi=150, bbox_inches="tight")
    plt.close()


def analyse_behavioral_patterns(customer, rental, payment):
    rental_freq = rental.groupby(
        "customer_id").size().reset_index(name="rental_count")
    payment_freq = payment.groupby(
        "customer_id").size().reset_index(name="payment_count")

    freq = rental_freq.merge(payment_freq, on="customer_id", how="left")
    freq["payment_count"] = freq["payment_count"].fillna(0)
    freq["return_rate"] = (freq["payment_count"] /
                           freq["rental_count"]).round(2)

    freq = freq.merge(
        customer[["customer_id", "first_name", "last_name"]],
        on="customer_id", how="inner"
    )
    freq["customer_name"] = freq["first_name"] + " " + freq["last_name"]
    freq = freq.drop(columns=["first_name", "last_name"])

    pending = freq[freq["return_rate"] < 1].nsmallest(10, "return_rate")[
        ["customer_name", "rental_count", "payment_count", "return_rate"]
    ]

    print("\nCustomers with Pending Returns (bottom 10):")
    print(pending.to_string(index=False))
    pending.to_csv(os.path.join(EXPORT_TABLES_DIR,
                   "customer_pending_returns.csv"), index=False)

    fig, ax = plt.subplots(figsize=(10, 5))
    sns.histplot(freq["return_rate"], bins=20, kde=True, ax=ax)
    ax.set_title("Customer Return Rate Distribution",
                 fontsize=14, fontweight="bold")
    ax.set_xlabel("Return Rate")
    ax.set_ylabel("Number of Customers")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    plt.tight_layout()
    plt.savefig(os.path.join(EXPORT_VIZ_DIR,
                "customer_return_rate.png"), dpi=150, bbox_inches="tight")
    plt.close()


if __name__ == "__main__":
    customer, rental, inventory, film_category, category, payment = load_data()

    # analyse_segmentation(payment)
    # analyse_lifetime_value(customer, payment, rental)
    # analyse_churn_risk(customer, rental)
    # analyse_behavioral_patterns(customer, rental, payment)

    POSTGRESQL_ENGINE.dispose()
