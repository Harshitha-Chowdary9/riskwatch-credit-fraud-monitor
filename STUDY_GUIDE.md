# Study guide

## Be able to explain in one minute
"I generated synthetic card data, loaded it in SQLite, wrote SQL for portfolio metrics and two monitoring rules, and measured the rules against cases I injected. I know the perfect scores are because the data is artificial."

## Key ideas
- **Utilisation** = balance / credit limit. High utilisation is an early stress signal.
- **DPD buckets**: 0 current, 1 = 1-29 days, 2 = 30-59, 3 = 60-89, 4 = charged off. "30+ delinquency" means bucket >= 2.
- **Roll rate**: share of accounts in bucket X that are in bucket Y next month. Forward rolls (1->2, 2->3) predict losses; the 1->0 share shows cures.
- **Card testing**: fraudsters try many tiny charges to check a stolen card works, then make one large one. Rule: burst of small charges in a short window.
- **Structuring**: splitting amounts to stay under a reporting threshold. Rule: several near-threshold amounts in a short window. A flag is a reason to review, not proof.
- **Precision vs recall**: precision = flagged that were truly bad; recall = bad cases that were flagged. Fraud teams trade them off against review workload.

## SQL points to know
- The rules use a self-join on the same customer with a time range, which is how you do a rolling window in SQLite without a range-window function.
- `roll_rates.sql` uses `SUM(COUNT(*)) OVER (PARTITION BY from_bucket)` to turn counts into shares.
- Join snapshots to themselves on `month + 1` to compare consecutive months.

## Likely questions
1. Why is precision 100% here? Because I injected clean patterns. On real data I would expect false positives (for example a merchant with many small legitimate charges).
2. How would you pick the thresholds? Look at the distribution of real transactions, test candidate thresholds on labelled history, and weigh review cost against missed fraud.
3. What would you add first? Data-quality checks, a time-based backtest, and segment-specific thresholds.
4. Where could an LLM help, and where not? Drafting commentary from verified aggregates, summarising case notes. Not for deciding credit or flagging customers without human review, and never with raw customer data in the prompt unless approved.
5. What are the weaknesses of the delinquency data? One hidden risk factor, no macro effects, no cohort/vintage analysis.

## Things I have not done
Vintage curves, a predictive credit model, real-time scoring, orchestration (Airflow etc.), dbt. Say so if asked.
