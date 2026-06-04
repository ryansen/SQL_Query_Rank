"""Schema for q002_monthly_revenue."""


def create_schema(conn) -> None:
    conn.execute("""
        CREATE TABLE orders (
            id          SERIAL PRIMARY KEY,
            order_date  DATE NOT NULL,
            amount      NUMERIC(10, 2) NOT NULL,
            status      TEXT NOT NULL CHECK (status IN ('completed', 'pending', 'cancelled'))
        )
    """)
    conn.execute("CREATE INDEX idx_orders_status_date ON orders(status, order_date)")
