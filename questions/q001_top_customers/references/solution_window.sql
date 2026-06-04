-- Reference: Subquery with explicit ranking
SELECT customer_name, total_revenue, order_count
FROM (
    SELECT
        c.name                                          AS customer_name,
        SUM(o.amount)                                   AS total_revenue,
        COUNT(o.id)                                     AS order_count,
        RANK() OVER (ORDER BY SUM(o.amount) DESC, c.name ASC) AS rnk
    FROM customers c
    JOIN orders o ON o.customer_id = c.id
    WHERE o.status = 'completed'
    GROUP BY c.id, c.name
) ranked
WHERE rnk <= 10
ORDER BY total_revenue DESC, customer_name ASC;
