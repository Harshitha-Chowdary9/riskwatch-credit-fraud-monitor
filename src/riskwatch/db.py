from __future__ import annotations

import sqlite3
from pathlib import Path

from .generate import generate

SQL_DIR = Path(__file__).resolve().parents[2] / "sql"


def build_db(path: str = ":memory:", n_customers: int = 600, seed: int = 7) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    customers, tx, snaps = generate(n_customers, seed)
    customers.to_sql("customers", conn, index=False, if_exists="replace")
    tx.to_sql("transactions", conn, index=False, if_exists="replace")
    snaps.to_sql("snapshots", conn, index=False, if_exists="replace")
    conn.execute("CREATE INDEX IF NOT EXISTS ix_tx_cust_ts ON transactions(customer_id, ts)")
    return conn


def run_sql(conn: sqlite3.Connection, name: str):
    """Run sql/<name>.sql and return a DataFrame."""
    import pandas as pd

    return pd.read_sql_query((SQL_DIR / f"{name}.sql").read_text(), conn)
