-- Roll rates: of accounts in bucket X last month, what share is in bucket Y this month.
WITH pairs AS (
    SELECT a.dpd_bucket AS from_bucket, b.dpd_bucket AS to_bucket
    FROM snapshots a
    JOIN snapshots b
      ON b.customer_id = a.customer_id AND b.month = a.month + 1
)
SELECT
    from_bucket,
    to_bucket,
    COUNT(*) AS n,
    ROUND(1.0 * COUNT(*) / SUM(COUNT(*)) OVER (PARTITION BY from_bucket), 4) AS share
FROM pairs
GROUP BY from_bucket, to_bucket
ORDER BY from_bucket, to_bucket;
