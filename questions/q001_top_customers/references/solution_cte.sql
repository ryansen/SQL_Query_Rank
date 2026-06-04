-- Reference: CTE approach
WITH completed_orders AS (
    SELECT customer_id, amount
    FROM orders
    WHERE status = 'completed'
),
customer_totals AS (
    SELECT
        c.name              AS customer_name,
        SUM(co.amount)      AS total_revenue,
        COUNT(co.customer_id) AS order_count
    FROM customers c
    JOIN completed_orders co ON co.customer_id = c.id
    GROUP BY c.id, c.name
)
SELECT customer_name, total_revenue, order_count
FROM customer_totals
ORDER BY total_revenue DESC, customer_name ASC
LIMIT 10;
