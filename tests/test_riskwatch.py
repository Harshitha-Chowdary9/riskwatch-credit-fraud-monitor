import sqlite3

import pandas as pd
import pytest

from riskwatch.db import build_db, run_sql
from riskwatch.generate import generate
from riskwatch.report import collect_metrics, llm_prompt, summarize
from riskwatch.rules import evaluate_rules


@pytest.fixture(scope="module")
def conn():
    return build_db(":memory:", n_customers=300, seed=1)


def test_generation_is_deterministic():
    a = generate(50, 3)[1]
    b = generate(50, 3)[1]
    pd.testing.assert_frame_equal(a, b)


def test_no_duplicate_ids_and_valid_buckets(conn):
    assert conn.execute("SELECT COUNT(*) - COUNT(DISTINCT tx_id) FROM transactions").fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM snapshots WHERE dpd_bucket NOT BETWEEN 0 AND 4").fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM transactions WHERE amount <= 0").fetchone()[0] == 0


def test_roll_rate_shares_sum_to_one(conn):
    roll = run_sql(conn, "roll_rates")
    sums = roll.groupby("from_bucket")["share"].sum()
    assert all(abs(s - 1) < 0.01 for s in sums)


def test_card_testing_rule_on_handmade_data():
    c = sqlite3.connect(":memory:")
    c.execute("CREATE TABLE transactions(tx_id, customer_id, ts, amount, category, is_bad, pattern)")
    rows = [(i, 1, f"2025-03-01 10:{i:02d}:00", 1.0, "x", 0, "") for i in range(5)]
    rows += [(10 + i, 2, f"2025-03-0{i + 1} 10:00:00", 1.0, "x", 0, "") for i in range(5)]  # spread out
    c.executemany("INSERT INTO transactions VALUES (?,?,?,?,?,?,?)", rows)
    flagged = set(run_sql(c, "fraud_card_testing")["customer_id"])
    assert flagged == {1}


def test_structuring_rule_needs_three_in_a_week():
    c = sqlite3.connect(":memory:")
    c.execute("CREATE TABLE transactions(tx_id, customer_id, ts, amount, category, is_bad, pattern)")
    rows = [(1, 1, "2025-03-01 10:00:00", 9500, "x", 0, ""), (2, 1, "2025-03-02 10:00:00", 9400, "x", 0, ""),
            (3, 1, "2025-03-03 10:00:00", 9300, "x", 0, ""),
            (4, 2, "2025-03-01 10:00:00", 9500, "x", 0, ""), (5, 2, "2025-03-20 10:00:00", 9400, "x", 0, ""),
            (6, 2, "2025-04-10 10:00:00", 9300, "x", 0, "")]
    c.executemany("INSERT INTO transactions VALUES (?,?,?,?,?,?,?)", rows)
    assert set(run_sql(c, "aml_structuring")["customer_id"]) == {1}


def test_rules_find_injected_cases(conn):
    r = evaluate_rules(conn).set_index("rule")
    assert r.loc["card_testing", "recall"] >= 0.9
    assert r.loc["structuring", "recall"] >= 0.9


def test_summary_and_prompt_contain_no_customer_rows(conn):
    m = collect_metrics(conn)
    text = summarize(m)
    assert "Portfolio:" in text and "customer_id" not in text
    assert "customer_id" not in llm_prompt(m)
