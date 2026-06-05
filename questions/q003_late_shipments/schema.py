"""Schema definition for this question."""


def create_schema(conn) -> None:
    """Create the tables needed for this question."""
    conn.execute("""
        CREATE TABLE example_table (
            id SERIAL PRIMARY KEY,
            created_at DATE NOT NULL,
            amount NUMERIC(10, 2) NOT NULL,
            status TEXT NOT NULL
        )
    """)

    conn.execute("CREATE INDEX idx_example_table_status ON example_table(status)")
