-- Month-level portfolio view: balances, utilisation, 30+ delinquency rate.
-- dpd_bucket: 0 current, 1 = 1-29 days, 2 = 30-59, 3 = 60-89, 4 = charged off.
SELECT
    s.month,
    COUNT(*)                                             AS accounts,
    ROUND(SUM(s.balance), 0)                             AS balance,
    ROUND(SUM(s.balance) / SUM(c.credit_limit), 4)       AS utilisation,
    ROUND(1.0 * SUM(s.dpd_bucket >= 2) / COUNT(*), 4)    AS dq30_rate,
    ROUND(SUM(CASE WHEN s.dpd_bucket >= 2 THEN s.balance ELSE 0 END)
          / SUM(s.balance), 4)                           AS dq30_balance_rate
FROM snapshots s
JOIN customers c USING (customer_id)
GROUP BY s.month
ORDER BY s.month;
