"""Generate fully synthetic card-portfolio data.

Nothing here comes from real customers. Fraud and structuring patterns are
injected on purpose so the rules have something to find, and each injected
row carries a ground-truth label so rule quality can be measured.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

CATEGORIES = ["grocery", "ads", "shipping", "software", "inventory", "travel", "dining", "electronics"]
START = pd.Timestamp("2025-01-01")
MONTHS = 12


def generate(n_customers: int = 600, seed: int = 7):
    rng = np.random.default_rng(seed)

    seg = rng.choice(["micro", "small", "growth"], size=n_customers, p=[0.5, 0.35, 0.15])
    limit_base = {"micro": 5_000, "small": 20_000, "growth": 75_000}
    risk_score = np.clip(rng.normal(0.35, 0.18, n_customers), 0.02, 0.95)
    customers = pd.DataFrame({
        "customer_id": np.arange(1, n_customers + 1),
        "segment": seg,
        "credit_limit": [limit_base[s] * rng.uniform(0.7, 1.4) for s in seg],
        "open_month": rng.integers(0, 6, n_customers),  # months since START
        "latent_risk": risk_score,
    })
    customers["credit_limit"] = customers["credit_limit"].round(-2)

    tx_rows = []
    snap_rows = []
    tid = 1
    for c in customers.itertuples():
        balance = 0.0
        delinq = 0  # months past due bucket: 0 current, 1 = 1-29d, 2 = 30-59d ... 4 = charged off
        for m in range(c.open_month, MONTHS):
            n_tx = rng.poisson(14 + 8 * (c.segment != "micro"))
            util_target = np.clip(rng.normal(0.25 + 0.5 * c.latent_risk, 0.1), 0.02, 1.0)
            month_spend_target = util_target * c.credit_limit
            amounts = rng.lognormal(mean=0, sigma=0.9, size=max(n_tx, 1))
            amounts = amounts / amounts.sum() * month_spend_target
            for a in amounts:
                day = int(rng.integers(0, 28))
                ts = START + pd.DateOffset(months=m) + pd.Timedelta(days=day, hours=int(rng.integers(7, 22)),
                                                                    minutes=int(rng.integers(0, 60)))
                tx_rows.append((tid, c.customer_id, ts, round(float(a), 2), rng.choice(CATEGORIES), 0, ""))
                tid += 1
            spend = float(amounts.sum())
            payment_ratio = np.clip(rng.normal(0.9 - 0.8 * c.latent_risk, 0.25), 0.0, 1.0)
            balance = max(balance * (1 - payment_ratio) + spend, 0.0)
            balance = min(balance, c.credit_limit * 1.05)
            # delinquency transition
            if delinq == 4:
                pass
            elif payment_ratio < 0.15 and c.latent_risk > 0.35:
                delinq = min(delinq + 1, 4)
            elif payment_ratio > 0.6:
                delinq = max(delinq - 1, 0) if delinq < 3 else delinq
            snap_rows.append((c.customer_id, m, round(balance, 2), delinq))

    tx = pd.DataFrame(tx_rows, columns=["tx_id", "customer_id", "ts", "amount", "category", "is_bad", "pattern"])

    # inject card-testing bursts: many small amounts within minutes, then one big one
    extra = []
    victims = rng.choice(customers["customer_id"], size=25, replace=False)
    for v in victims:
        base = START + pd.Timedelta(days=int(rng.integers(30, 330)), hours=int(rng.integers(0, 5)))
        for i in range(int(rng.integers(6, 12))):
            extra.append((tid, v, base + pd.Timedelta(minutes=i * 2), round(float(rng.uniform(0.5, 4.0)), 2),
                          "software", 1, "card_testing")); tid += 1
        extra.append((tid, v, base + pd.Timedelta(minutes=30), round(float(rng.uniform(900, 2500)), 2),
                      "electronics", 1, "card_testing")); tid += 1

    # inject structuring-like behaviour: repeated amounts just under a 10,000 reporting-style threshold
    for v in rng.choice(customers["customer_id"], size=12, replace=False):
        start_day = int(rng.integers(20, 300))
        for i in range(int(rng.integers(4, 8))):
            extra.append((tid, v, START + pd.Timedelta(days=start_day + i, hours=11),
                          round(float(rng.uniform(9_000, 9_900)), 2), "inventory", 1, "structuring")); tid += 1

    tx = pd.concat([tx, pd.DataFrame(extra, columns=tx.columns)], ignore_index=True)
    tx["ts"] = pd.to_datetime(tx["ts"]).dt.strftime("%Y-%m-%d %H:%M:%S")
    tx = tx.sort_values("ts").reset_index(drop=True)

    snaps = pd.DataFrame(snap_rows, columns=["customer_id", "month", "balance", "dpd_bucket"])
    customers = customers.drop(columns="latent_risk")
    return customers, tx, snaps
