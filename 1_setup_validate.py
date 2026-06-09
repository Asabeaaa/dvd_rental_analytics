import os
import pandas as pd
from sqlalchemy import create_engine, text
from settings import settings

POSTGRESQL_ENGINE = create_engine(
    f"postgresql+psycopg2://{settings.DB_USER}:{settings.DB_PASSWORD}@{settings.DB_HOST}:5432/{settings.DB_NAME}"
)

CRITICAL_TABLES = [
    "film", "customer", "rental", "payment", "inventory", "store"
]

EXPORT_TABLES_DIR = os.path.join(os.path.dirname(
    os.path.abspath("__file__")), "exports", "tables")
os.makedirs(EXPORT_TABLES_DIR, exist_ok=True)


def return_all_tables() -> list:
    with POSTGRESQL_ENGINE.begin() as conn:
        result = conn.execute(text(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_type = 'BASE TABLE';"
        ))
        return [row[0] for row in result.fetchall()]


def validate_critical_tables(available_tables: list) -> tuple:
    missing = [table for table in CRITICAL_TABLES if table not in available_tables]
    present = [table for table in CRITICAL_TABLES if table in available_tables]
    return present, missing


def get_row_counts(available_tables: list) -> dict[str, int]:
    counts = {}
    with POSTGRESQL_ENGINE.begin() as conn:
        for table in available_tables:
            result = conn.execute(text(f"SELECT COUNT(*) FROM {table};"))
            counts[table] = result.scalar()
    return counts


def identify_data_quality_issues() -> dict[str, int]:
    issues = {}
    queries = {
        "actor": "SELECT COUNT(*) FROM actor WHERE first_name IS NULL OR last_name IS NULL;",
        "address": "SELECT COUNT(*) FROM address WHERE address IS NULL",
        "category": "SELECT COUNT(*) FROM category WHERE name IS NULL",
        "city": "SELECT COUNT(*) FROM city WHERE city IS NULL",
        "country": "SELECT COUNT(*) FROM country WHERE country IS NULL",
        "customer": "SELECT COUNT(*) FROM customer WHERE first_name IS NULL OR last_name IS NULL;",
        "film": "SELECT COUNT(*) FROM film WHERE title IS NULL OR rental_rate IS NULL OR replacement_cost IS NULL;",
        "rental": "SELECT COUNT(*) FROM rental WHERE rental_date IS NULL OR inventory_id IS NULL OR customer_id IS NULL;",
        "payment": "SELECT COUNT(*) FROM payment WHERE amount IS NULL OR amount < 0;",
        "store": "SELECT COUNT(*) FROM store WHERE manager_staff_id IS NULL OR address_id IS NULL;",
    }
    with POSTGRESQL_ENGINE.begin() as conn:
        for table, query in queries.items():
            result = conn.execute(text(query))
            issues[table] = result.scalar()
    return issues


def produce_validation_report(tables: list, present: list, missing: list,
                              row_counts: dict, quality_issues: dict) -> None:
    rows = []
    for table in tables:
        rows.append({
            "table": table,
            "is_critical": table in CRITICAL_TABLES,
            "critical_status": "present" if table in present else ("missing" if table in missing else "n/a"),
            "row_count": row_counts.get(table),
            "quality_issues": quality_issues.get(table, 0),
            "quality_status": "fail" if quality_issues.get(table, 0) > 0 else "pass",
        })

    report = pd.DataFrame(rows).sort_values(
        by=["is_critical", "table"], ascending=[False, True])
    print("\nValidation Report:")
    print(report.to_string(index=False))
    report.to_csv(os.path.join(EXPORT_TABLES_DIR,
                  "validation_report.csv"), index=False)


if __name__ == "__main__":
    tables = return_all_tables()
    present, missing = validate_critical_tables(tables)
    row_counts = get_row_counts(tables)
    quality_issues = identify_data_quality_issues()

    print("All available tables:", tables)
    print("Critical tables present:", present)
    print("Critical tables missing:", missing)
    print("Row counts of tables:", row_counts)
    print("Data quality issues identified:", quality_issues)

    produce_validation_report(tables, present, missing,
                              row_counts, quality_issues)

    POSTGRESQL_ENGINE.dispose()
