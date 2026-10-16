-- Latest-month risk by customer segment.
SELECT
    c.segment,
    COUNT(*)                                          AS accounts,
    ROUND(AVG(c.credit_limit), 0)                     AS avg_limit,
    ROUND(SUM(s.balance) / SUM(c.credit_limit), 4)    AS utilisation,
    ROUND(1.0 * SUM(s.dpd_bucket >= 2) / COUNT(*), 4) AS dq30_rate
FROM snapshots s
JOIN customers c USING (customer_id)
WHERE s.month = (SELECT MAX(month) FROM snapshots)
GROUP BY c.segment
ORDER BY dq30_rate DESC;
