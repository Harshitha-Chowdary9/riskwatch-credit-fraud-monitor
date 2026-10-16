from __future__ import annotations

import pandas as pd

from .db import run_sql

RULES = {"card_testing": "fraud_card_testing", "structuring": "aml_structuring"}


def evaluate_rules(conn) -> pd.DataFrame:
    """Customer-level precision / recall of each rule against the injected labels."""
    truth = pd.read_sql_query(
        "SELECT customer_id, pattern FROM transactions WHERE is_bad = 1 GROUP BY customer_id, pattern", conn
    )
    n_customers = pd.read_sql_query("SELECT COUNT(*) AS n FROM customers", conn)["n"][0]
    rows = []
    for rule, sql_name in RULES.items():
        flagged = set(run_sql(conn, sql_name)["customer_id"])
        actual = set(truth.loc[truth["pattern"] == rule, "customer_id"])
        tp = len(flagged & actual)
        fp = len(flagged - actual)
        fn = len(actual - flagged)
        rows.append({
            "rule": rule,
            "flagged": len(flagged),
            "true_positive": tp,
            "false_positive": fp,
            "missed": fn,
            "precision": round(tp / len(flagged), 3) if flagged else None,
            "recall": round(tp / len(actual), 3) if actual else None,
            "flag_rate": round(len(flagged) / n_customers, 4),
        })
    return pd.DataFrame(rows)
