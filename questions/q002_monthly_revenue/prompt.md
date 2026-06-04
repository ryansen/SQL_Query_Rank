# Monthly Revenue Trend

You have an `orders` table:

| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER | primary key |
| order_date | DATE | |
| amount | NUMERIC(10,2) | |
| status | TEXT | 'completed', 'pending', 'cancelled' |

## Task

Write a query that returns **total revenue per month** for **completed orders only**.

Your result must include:
- `month` — formatted as `YYYY-MM` (e.g. `2023-07`)
- `total_revenue` — sum of amounts for that month

Ordered by `month` ascending (oldest first).

**Include only months that have at least one completed order.**

## Hints

- Use `TO_CHAR(order_date, 'YYYY-MM')` to format the month
- Filter on `status = 'completed'`
- No LIMIT needed — return all months
