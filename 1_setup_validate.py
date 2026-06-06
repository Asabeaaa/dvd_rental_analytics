import os
import pandas as pd
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
print(POSTGRESQL_ENGINE)

CRITICAL_TABLES = [
    "film", "actor", "customer", "rental", "payment",
    "inventory", "store", "staff", "address", "category"
]


def return_all_tables():
    with POSTGRESQL_ENGINE.begin() as conn:
        result = conn.execute(text(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_type = 'BASE TABLE';"
        ))
        return [row[0] for row in result.fetchall()]


def validate_critical_tables(available_tables):
    missing = [t for t in CRITICAL_TABLES if t not in available_tables]
    present = [t for t in CRITICAL_TABLES if t in available_tables]
    return present, missing


def get_row_counts(tables):
    counts = {}
    with POSTGRESQL_ENGINE.begin() as conn:
        for table in tables:
            result = conn.execute(text(f"SELECT COUNT(*) FROM {table};"))
            counts[table] = result.scalar()
    return counts


def identify_data_quality_issues():
    issues = {}
    queries = {
        "film": "SELECT COUNT(*) FROM film WHERE title IS NULL OR rental_rate IS NULL OR release_year IS NULL;",
        "actor": "SELECT COUNT(*) FROM actor WHERE first_name IS NULL OR last_name IS NULL;",
        "customer": "SELECT COUNT(*) FROM customer WHERE email IS NULL;",
        "rental": "SELECT COUNT(*) FROM rental WHERE rental_date IS NULL OR inventory_id IS NULL OR customer_id IS NULL;",
        "payment": "SELECT COUNT(*) FROM payment WHERE amount IS NULL OR amount < 0;",
    }
    with POSTGRESQL_ENGINE.begin() as conn:
        for table, query in queries.items():
            result = conn.execute(text(query))
            issues[table] = result.scalar()
    return issues


if __name__ == "__main__":
    tables = return_all_tables()
    present, missing = validate_critical_tables(tables)
    row_counts = get_row_counts(tables)
    quality_issues = identify_data_quality_issues()

    summary = {
        "all_tables": tables,
        "critical_tables_present": present,
        "critical_tables_missing": missing,
        "row_counts": row_counts,
        "data_quality_issues": quality_issues,
    }

    for key, value in summary.items():
        print(f"\n{key}:")
        print(value)

    # close connection pool
    POSTGRESQL_ENGINE.dispose()
