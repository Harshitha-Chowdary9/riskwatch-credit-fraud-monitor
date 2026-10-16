-- Rule: card testing. 5+ transactions under 5.00 within a 60 minute window for one customer.
-- Uses a self-join over a per-customer window; flags every small transaction in the burst.
WITH small AS (
    SELECT tx_id, customer_id, ts, amount, is_bad, pattern
    FROM transactions
    WHERE amount < 5.0
),
burst AS (
    SELECT a.tx_id, a.customer_id, COUNT(*) AS small_tx_in_hour
    FROM small a
    JOIN small b
      ON b.customer_id = a.customer_id
     AND b.ts BETWEEN datetime(a.ts, '-60 minutes') AND a.ts
    GROUP BY a.tx_id, a.customer_id
    HAVING COUNT(*) >= 5
)
SELECT DISTINCT customer_id, 'card_testing' AS rule FROM burst
ORDER BY customer_id;
