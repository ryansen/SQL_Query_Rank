-- Reference: JOIN aggregation approach
SELECT
    c.name              AS customer_name,
    SUM(o.amount)       AS total_revenue,
    COUNT(o.id)         AS order_count
FROM customers c
JOIN orders o ON o.customer_id = c.id AND o.status = 'completed'
GROUP BY c.id, c.name
ORDER BY total_revenue DESC, customer_name ASC
LIMIT 10;
