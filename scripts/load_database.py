#!/usr/bin/env python3
"""
Module 3: Database Loader (load_database.py)
Executes sql/schema.sql and loads transformed star-schema tables into SQLite database.
"""

import os
import sqlite3
import pandas as pd


def build_sqlite_database(processed_dir: str, schema_path: str, db_path: str) -> dict:
    """Creates SQLite database from schema.sql and populates all 8 tables."""
    if os.path.exists(db_path):
        os.remove(db_path)

    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON;")

    with open(schema_path, "r", encoding="utf-8") as f:
        conn.executescript(f.read())

    load_order = [
        "dim_patient",
        "dim_organization",
        "dim_provider",
        "dim_date",
        "fact_encounter",
        "fact_condition",
        "fact_observation",
        "fact_medication",
    ]

    row_counts = {}
    for table in load_order:
        csv_path = os.path.join(processed_dir, f"{table}.csv")
        df = pd.read_csv(csv_path)
        df.to_sql(table, conn, if_exists="append", index=False)
        cur = conn.execute(f"SELECT COUNT(*) FROM {table}")
        row_counts[table] = cur.fetchone()[0]

    conn.commit()
    conn.close()
    return row_counts


if __name__ == "__main__":
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    counts = build_sqlite_database(
        os.path.join(repo_root, "data", "processed"),
        os.path.join(repo_root, "sql", "schema.sql"),
        os.path.join(repo_root, "data", "processed", "hospital_analytics.db")
    )
    print("Loaded SQLite database tables:", counts)
