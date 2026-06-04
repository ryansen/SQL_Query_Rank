-- Reference: TO_CHAR grouping
SELECT
    TO_CHAR(order_date, 'YYYY-MM') AS month,
    SUM(amount)                    AS total_revenue
FROM orders
WHERE status = 'completed'
GROUP BY TO_CHAR(order_date, 'YYYY-MM')
ORDER BY month ASC;
