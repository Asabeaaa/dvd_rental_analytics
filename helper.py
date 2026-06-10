from sqlalchemy import text
import pandas as pd


TABLES = ["actor", "store", "address", "category", "city", "country",
          "customer", "film_actor", "film_category", "inventory",
          "language", "rental", "staff", "payment", "film"]


def load_tables(db_engine) -> dict:
    dataframes = {}
    with db_engine.begin() as conn:
        for table in TABLES:
            dataframes[table] = pd.read_sql(
                text(f"SELECT * FROM {table};"), conn)
    return dataframes
