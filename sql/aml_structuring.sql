-- Rule: structuring-like behaviour. 3+ transactions between 9,000 and 9,999.99
-- inside a rolling 7 day window for one customer (just under a 10,000 reporting-style threshold).
-- The threshold is an illustrative parameter, not a statement about any specific regulation.
WITH near AS (
    SELECT tx_id, customer_id, ts
    FROM transactions
    WHERE amount >= 9000 AND amount < 10000
),
win AS (
    SELECT a.customer_id, a.tx_id, COUNT(*) AS n_in_week
    FROM near a
    JOIN near b
      ON b.customer_id = a.customer_id
     AND b.ts BETWEEN datetime(a.ts, '-7 days') AND a.ts
    GROUP BY a.customer_id, a.tx_id
    HAVING COUNT(*) >= 3
)
SELECT DISTINCT customer_id, 'structuring' AS rule FROM win
ORDER BY customer_id;
