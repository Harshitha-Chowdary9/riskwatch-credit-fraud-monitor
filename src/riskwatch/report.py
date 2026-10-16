from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from .db import run_sql
from .rules import evaluate_rules


def collect_metrics(conn) -> dict:
    return {
        "monthly": run_sql(conn, "portfolio_monthly"),
        "roll": run_sql(conn, "roll_rates"),
        "segments": run_sql(conn, "segment_risk"),
        "rules": evaluate_rules(conn),
    }


def summarize(m: dict) -> str:
    """Plain-text summary written from the numbers. Deterministic, no model involved."""
    mo, seg, rules = m["monthly"], m["segments"], m["rules"]
    last, first = mo.iloc[-1], mo.iloc[0]
    worst = seg.iloc[0]
    roll = m["roll"]
    r12 = roll[(roll.from_bucket == 1) & (roll.to_bucket == 2)]
    r12 = float(r12["share"].iloc[0]) if len(r12) else float("nan")
    lines = [
        f"Portfolio: {int(last.accounts)} accounts, balance {last.balance:,.0f}, utilisation {last.utilisation:.1%}.",
        f"30+ day delinquency moved from {first.dq30_rate:.1%} (month {int(first.month)}) to {last.dq30_rate:.1%} (month {int(last.month)}).",
        f"Highest-risk segment: {worst.segment} ({worst.dq30_rate:.1%} 30+ delinquent, utilisation {worst.utilisation:.1%}).",
        f"Roll rate from 1-29 days to 30-59 days: {r12:.1%}.",
    ]
    for r in rules.itertuples():
        lines.append(f"Rule {r.rule}: flagged {r.flagged} customers, precision {r.precision}, recall {r.recall}.")
    return "\n".join(lines)


def llm_prompt(m: dict) -> str:
    """Build a prompt for an LLM to draft a commentary. Only aggregate numbers go in.

    This repo does not call any model. It shows the safe shape of the input: aggregates only,
    no customer rows, and an instruction to refuse to invent numbers. A reviewer must still read the output.
    """
    return (
        "You are drafting a short weekly risk note for a credit team. Use only the figures below. "
        "If a figure is missing, say so. Do not give causes you cannot see in the data.\n\n" + summarize(m)
    )


def dashboard(m: dict, path: str) -> None:
    fig, ax = plt.subplots(2, 2, figsize=(12, 8))
    mo = m["monthly"]
    ax[0, 0].plot(mo["month"], mo["dq30_rate"] * 100, marker="o", color="#c0392b")
    ax[0, 0].set_title("30+ day delinquency rate (%)")
    ax[0, 0].set_xlabel("month")

    ax[0, 1].plot(mo["month"], mo["utilisation"] * 100, marker="o", color="#2c3e50")
    ax[0, 1].set_title("Portfolio utilisation (%)")
    ax[0, 1].set_xlabel("month")

    roll = m["roll"]
    piv = roll.pivot(index="from_bucket", columns="to_bucket", values="share").fillna(0)
    im = ax[1, 0].imshow(piv.values, cmap="Reds", vmin=0, vmax=1)
    ax[1, 0].set_xticks(range(len(piv.columns)), piv.columns)
    ax[1, 0].set_yticks(range(len(piv.index)), piv.index)
    ax[1, 0].set_xlabel("to bucket")
    ax[1, 0].set_ylabel("from bucket")
    ax[1, 0].set_title("Roll rates (row = share)")
    for i in range(piv.shape[0]):
        for j in range(piv.shape[1]):
            v = piv.values[i, j]
            ax[1, 0].text(j, i, f"{v:.0%}", ha="center", va="center", color="white" if v > 0.5 else "black", fontsize=8)
    fig.colorbar(im, ax=ax[1, 0], fraction=0.046)

    r = m["rules"]
    x = range(len(r))
    ax[1, 1].bar([i - 0.2 for i in x], r["precision"].fillna(0), width=0.4, label="precision", color="#2980b9")
    ax[1, 1].bar([i + 0.2 for i in x], r["recall"].fillna(0), width=0.4, label="recall", color="#27ae60")
    ax[1, 1].set_xticks(list(x), r["rule"])
    ax[1, 1].set_ylim(0, 1.05)
    ax[1, 1].set_title("Rule quality on injected synthetic cases")
    ax[1, 1].legend(loc="lower right")

    fig.suptitle("riskwatch dashboard (synthetic data)", fontsize=14)
    fig.tight_layout()
    fig.savefig(path, dpi=110)
    plt.close(fig)
