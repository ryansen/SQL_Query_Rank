"""Schema definition for q001_top_customers."""


def create_schema(conn) -> None:
    """Create the tables needed for this question."""
    conn.execute("""
        CREATE TABLE customers (
            id      SERIAL PRIMARY KEY,
            name    TEXT NOT NULL,
            email   TEXT UNIQUE NOT NULL,
            region  TEXT NOT NULL
        )
    """)

    conn.execute("""
        CREATE TABLE orders (
            id          SERIAL PRIMARY KEY,
            customer_id INTEGER NOT NULL REFERENCES customers(id),
            order_date  DATE NOT NULL,
            amount      NUMERIC(10, 2) NOT NULL,
            status      TEXT NOT NULL CHECK (status IN ('completed', 'pending', 'cancelled'))
        )
    """)

    conn.execute("CREATE INDEX idx_orders_customer_id ON orders(customer_id)")
    conn.execute("CREATE INDEX idx_orders_status ON orders(status)")
