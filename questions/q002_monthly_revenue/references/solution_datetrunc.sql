-- Reference: DATE_TRUNC approach (equivalent, formatted in SELECT)
SELECT
    TO_CHAR(DATE_TRUNC('month', order_date), 'YYYY-MM') AS month,
    SUM(amount)                                          AS total_revenue
FROM orders
WHERE status = 'completed'
GROUP BY DATE_TRUNC('month', order_date)
ORDER BY DATE_TRUNC('month', order_date) ASC;
