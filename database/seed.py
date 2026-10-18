
from database.db import get_connection, initialize_database


def seed_database():
    """Insert synthetic demo data into the database."""

    initialize_database()

    customers = [
        ("CUST001", "Aarav Mehta", "aarav@example.com"),
        ("CUST002", "Priya Shah", "priya@example.com"),
        ("CUST003", "Kabir Verma", "kabir@example.com"),
        ("CUST004", "Anaya Rao", "anaya@example.com"),
        ("CUST005", "Rohan Das", "rohan@example.com"),
    ]

    orders = [
        ("ORD1001", "CUST001", "Wireless Mouse", 799.0,
         "DELIVERED", "2026-10-10", "2026-10-12"),
        ("ORD1002", "CUST002", "Keyboard", 1499.0,
         "DELIVERED", "2026-10-08", "2026-10-10"),
        ("ORD1003", "CUST003", "Headphones", 2999.0,
         "DELIVERED", "2026-10-01", "2026-10-03"),
        ("ORD1004", "CUST004", "Monitor", 12999.0,
         "SHIPPED", "2026-10-15", None),
        ("ORD1005", "CUST005", "USB Cable", 299.0,
         "DELIVERED", "2026-10-14", "2026-10-16"),
    ]

    policies = [
        (
            "Standard Refund Policy",
            "Eligible delivered items may be considered for "
            "refund within 30 days of delivery. Exceptions "
            "and risk flags require review.",
            30,
            2000.0,
            1,
        )
    ]

    cases = [
        (
            "CASE001", "CUST001", "ORD1001",
            "The mouse arrived damaged.", "OPEN",
            "UNKNOWN", None,
        ),
        (
            "CASE002", "CUST002", "ORD1002",
            "I want to return the keyboard.", "OPEN",
            "UNKNOWN", None,
        ),
        (
            "CASE003", "CUST003", "ORD1003",
            "I received the wrong product.", "OPEN",
            "UNKNOWN", None,
        ),
        (
            "CASE004", "CUST004", "ORD1004",
            "I want to cancel my order.", "OPEN",
            "UNKNOWN", None,
        ),
        (
            "CASE005", "CUST005", "ORD1005",
            "The cable is not working.", "OPEN",
            "UNKNOWN", None,
        ),
    ]

    with get_connection() as connection:
        connection.executemany(
            """
            INSERT OR IGNORE INTO customers
            (customer_id, name, email)
            VALUES (?, ?, ?)
            """,
            customers,
        )

        connection.executemany(
            """
            INSERT OR IGNORE INTO orders
            (order_id, customer_id, item_name, amount,
             order_status, purchase_date, delivery_date)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            orders,
        )

        connection.executemany(
            """
            INSERT INTO refund_policies
            (policy_name, description, return_window_days,
             max_auto_refund, active)
            SELECT ?, ?, ?, ?, ?
            WHERE NOT EXISTS (
                SELECT 1 FROM refund_policies
                WHERE policy_name = ?
            )
            """,
            [(*policy, policy[0]) for policy in policies],
        )

        connection.executemany(
            """
            INSERT OR IGNORE INTO customer_cases
            (case_id, customer_id, order_id, issue, status,
             risk_level, decision)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            cases,
        )

    print("Database initialized successfully!")
    print("Synthetic customers, orders, policies and cases are ready.")


if __name__ == "__main__":
    seed_database()
