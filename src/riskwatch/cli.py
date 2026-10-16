from __future__ import annotations

import argparse
from pathlib import Path

from .db import build_db
from .report import collect_metrics, dashboard, summarize


def main(argv=None):
    p = argparse.ArgumentParser(description="Run the riskwatch pipeline on synthetic data.")
    p.add_argument("--customers", type=int, default=600)
    p.add_argument("--seed", type=int, default=7)
    p.add_argument("--out", default="out")
    a = p.parse_args(argv)

    out = Path(a.out)
    out.mkdir(exist_ok=True)
    conn = build_db(str(out / "riskwatch.db"), a.customers, a.seed)
    m = collect_metrics(conn)
    for name, df in m.items():
        df.to_csv(out / f"{name}.csv", index=False)
    dashboard(m, str(out / "dashboard.png"))
    text = summarize(m)
    (out / "summary.txt").write_text(text + "\n")
    print(text)
    print(f"\nWrote CSVs, summary.txt and dashboard.png to {out}/")


if __name__ == "__main__":
    main()
