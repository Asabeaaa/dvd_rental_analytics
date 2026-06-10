import os
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from sqlalchemy import create_engine
from settings import settings
from helper import load_tables
from advanced_analytics.customer_analytics import (analyse_segmentation, analyse_lifetime_value,
                                                   analyse_churn_risk, analyse_behavioral_patterns)
from advanced_analytics.revenue_optimization import (analyse_category_performance, analyse_temporal_trends,
                                                     analyse_pricing_insights)

BASE_DIR = os.path.dirname(os.path.abspath("__file__"))

POSTGRESQL_ENGINE = create_engine(
    f"postgresql+psycopg2://{settings.DB_USER}:{settings.DB_PASSWORD}@{settings.DB_HOST}:5432/{settings.DB_NAME}"
)


EXPORT_MERGES_DIR = os.path.join(BASE_DIR, "exports", "merges")


plt.style.use("seaborn-v0_8-whitegrid")
sns.set_palette("husl")


def load_data():
    category_revenue = pd.read_csv(
        os.path.join(EXPORT_MERGES_DIR, "category_revenue.csv"),
        parse_dates=["payment_date"]
    )
    category_rental_volume = pd.read_csv(
        os.path.join(EXPORT_MERGES_DIR, "category_rental_volume.csv"),
        parse_dates=["rental_date"]
    )
    dataframes = load_tables(POSTGRESQL_ENGINE)
    customer = dataframes["customer"]
    rental = dataframes["rental"]
    inventory = dataframes["inventory"]
    film_category = dataframes["film_category"]
    category = dataframes["category"]
    payment = dataframes["payment"]
    return category_revenue, category_rental_volume, customer, rental, inventory, film_category, category, payment


if __name__ == "__main__":
    category_revenue, category_rental_volume, customer, rental, inventory, film_category, category, payment = load_data()

    # # customer analytics
    # analyse_segmentation(payment)
    # analyse_lifetime_value(customer, payment, rental)
    # analyse_churn_risk(customer, rental)
    # analyse_behavioral_patterns(customer, rental, payment)

    # # revenue optimization
    # analyse_category_performance(category_revenue, category_rental_volume)
    # analyse_temporal_trends(category_rental_volume)
    analyse_pricing_insights(category_revenue, category_rental_volume)

    POSTGRESQL_ENGINE.dispose()
