# Top Customers by Revenue

You have two tables: `customers` and `orders`.

**customers**
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER | primary key |
| name | TEXT | customer full name |
| email | TEXT | unique |
| region | TEXT | e.g. 'North', 'South', 'East', 'West' |

**orders**
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER | primary key |
| customer_id | INTEGER | FK → customers.id |
| order_date | DATE | |
| amount | NUMERIC(10,2) | order total |
| status | TEXT | 'completed', 'pending', 'cancelled' |

## Task

Write a query that returns the **top 10 customers** ranked by their **total revenue from completed orders only**.

Your result must include:
- `customer_name`
- `total_revenue` (sum of completed order amounts)
- `order_count` (number of completed orders)

Ordered by `total_revenue` descending, then `customer_name` ascending for ties.

**Exclude customers with zero completed orders.**

## Hints

- Remember to filter on `status = 'completed'`
- Ties in revenue should be broken alphabetically by name
- LIMIT to exactly 10 rows
