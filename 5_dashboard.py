import os
import pandas as pd
import streamlit as st
from PIL import Image

BASE_DIR = os.path.dirname(os.path.abspath("__file__"))
EXPORT_TABLES_DIR = os.path.join(BASE_DIR, "exports", "tables")
EXPORT_VIZ_DIR = os.path.join(BASE_DIR, "exports", "visualizations")
EXPORT_MERGES_DIR = os.path.join(BASE_DIR, "exports", "merges")

GOALS = {
    "monthly_revenue": 5000,
    "active_customers": 500,
    "monthly_rentals": 1500,
    "high_segment_customers": 1000,
}


def kpi_trend(label, current, previous):
    delta = current - previous
    pct = (delta / previous * 100) if previous else 0
    arrow = "▲" if delta >= 0 else "▼"
    st.metric(
        label=label,
        value=f"{current:,.2f}",
        delta=f"{arrow} {abs(pct):.1f}% vs last month"
    )


def kpi_goal(label, actual, target):
    pct = min(actual / target, 1.0) if target else 0
    st.markdown(f"**{label}**")
    st.markdown(f"{actual:,.0f} of {target:,} ({pct*100:.1f}%)")
    st.progress(pct)


def get_monthly_revenue(category_revenue):
    category_revenue["payment_date"] = pd.to_datetime(
        category_revenue["payment_date"])
    monthly = category_revenue.groupby(
        category_revenue["payment_date"].dt.to_period("M")
    )["amount"].sum()
    current = float(monthly.iloc[-1]) if len(monthly) >= 1 else 0
    previous = float(monthly.iloc[-2]) if len(monthly) >= 2 else 0
    return current, previous


def get_monthly_rentals(category_rental_volume):
    category_rental_volume["rental_date"] = pd.to_datetime(
        category_rental_volume["rental_date"])
    monthly = category_rental_volume.groupby(
        category_rental_volume["rental_date"].dt.to_period("M")
    ).size()
    current = int(monthly.iloc[-1]) if len(monthly) >= 1 else 0
    previous = int(monthly.iloc[-2]) if len(monthly) >= 2 else 0
    return current, previous


@st.cache_data
def load_data():
    category_revenue = pd.read_csv(os.path.join(
        EXPORT_MERGES_DIR, "category_revenue.csv"))
    category_rental_volume = pd.read_csv(os.path.join(
        EXPORT_MERGES_DIR, "category_rental_volume.csv"))
    churn = pd.read_csv(os.path.join(
        EXPORT_TABLES_DIR, "customer_churn_risk.csv"))
    segments = pd.read_csv(os.path.join(
        EXPORT_TABLES_DIR, "customer_segments.csv"))
    store = pd.read_csv(os.path.join(
        EXPORT_TABLES_DIR, "store_comparison.csv"))
    return category_revenue, category_rental_volume, churn, segments, store


def img(filename):
    return Image.open(os.path.join(EXPORT_VIZ_DIR, filename))


def page_customer(churn, segments):
    st.header("Customer Analytics")

    active_customers = int((churn["churn_risk"] == "active").sum())
    high_segment = int(segments[segments["segment"]
                       == "high"]["customer_count"].values[0])

    col1, col2 = st.columns(2)
    with col1:
        kpi_goal("Active Customers", active_customers,
                 GOALS["active_customers"])
    with col2:
        kpi_goal("High Segment Customers", high_segment,
                 GOALS["high_segment_customers"])

    st.subheader("Customer Segmentation")
    st.image(img("customer_segments.png"))

    st.subheader("Lifetime Value Distribution")
    st.image(img("customer_ltv_distribution.png"))

    st.subheader("Churn Risk")
    st.image(img("customer_churn_risk.png"))

    st.subheader("Return Rate Distribution")
    st.image(img("customer_return_rate.png"))


def page_revenue(category_revenue, category_rental_volume):
    st.header("Revenue Optimization")

    current_rev, previous_rev = get_monthly_revenue(category_revenue)
    current_rentals, previous_rentals = get_monthly_rentals(
        category_rental_volume)

    col1, col2 = st.columns(2)
    with col1:
        kpi_trend("Monthly Revenue", current_rev, previous_rev)
    with col2:
        kpi_goal("Monthly Rentals", current_rentals, GOALS["monthly_rentals"])

    st.subheader("Category Performance")
    st.image(img("category_performance.png"))

    st.subheader("Temporal Trends")
    st.image(img("temporal_trends.png"))

    st.subheader("Pricing Insights")
    st.image(img("pricing_insights.png"))


def page_inventory(category_rental_volume, store):
    st.header("Inventory & Operations")

    current_rentals, previous_rentals = get_monthly_rentals(
        category_rental_volume)
    total_rentals = int(store["rental_count"].sum())

    col1, col2 = st.columns(2)
    with col1:
        kpi_trend("Monthly Rentals", current_rentals, previous_rentals)
    with col2:
        kpi_goal("Total Rentals Target", total_rentals,
                 GOALS["monthly_rentals"] * 12)

    st.subheader("Film Turnover")
    st.image(img("film_turnover.png"))

    st.subheader("Store Comparison")
    st.image(img("store_comparison.png"))

    st.subheader("Stock Efficiency")
    st.image(img("stock_efficiency.png"))


def main():
    st.set_page_config(page_title="DVD Rental Analytics", layout="wide")
    st.title("DVD Rental Analytics")

    category_revenue, category_rental_volume, churn, segments, store = load_data()

    page = st.sidebar.radio("Navigation", [
        "Customer Analytics",
        "Revenue Optimization",
        "Inventory & Operations",
    ])

    if page == "Customer Analytics":
        page_customer(churn, segments)
    elif page == "Revenue Optimization":
        page_revenue(category_revenue, category_rental_volume)
    elif page == "Inventory & Operations":
        page_inventory(category_rental_volume, store)


if __name__ == "__main__":
    main()
