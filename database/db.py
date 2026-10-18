
import sqlite3
from pathlib import Path

# Database file will be created inside the database folder.
DATABASE_PATH = Path(__file__).resolve().parent / "resolveai.db"


def get_connection():
    """Create a connection to the SQLite database."""
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_database():
    """Create the tables required by ResolveAI."""

    with get_connection() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS customers (
                customer_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS orders (
                order_id TEXT PRIMARY KEY,
                customer_id TEXT NOT NULL,
                item_name TEXT NOT NULL,
                amount REAL NOT NULL CHECK(amount > 0),
                order_status TEXT NOT NULL,
                purchase_date TEXT NOT NULL,
                delivery_date TEXT,
                FOREIGN KEY (customer_id)
                    REFERENCES customers(customer_id)
            );

            CREATE TABLE IF NOT EXISTS refund_policies (
                policy_id INTEGER PRIMARY KEY AUTOINCREMENT,
                policy_name TEXT NOT NULL,
                description TEXT NOT NULL,
                return_window_days INTEGER NOT NULL,
                max_auto_refund REAL NOT NULL,
                active INTEGER NOT NULL DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS customer_cases (
                case_id TEXT PRIMARY KEY,
                customer_id TEXT NOT NULL,
                order_id TEXT NOT NULL,
                issue TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'OPEN',
                risk_level TEXT DEFAULT 'UNKNOWN',
                decision TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (customer_id)
                    REFERENCES customers(customer_id),
                FOREIGN KEY (order_id)
                    REFERENCES orders(order_id)
            );

            CREATE TABLE IF NOT EXISTS refunds (
                refund_id INTEGER PRIMARY KEY AUTOINCREMENT,
                case_id TEXT NOT NULL UNIQUE,
                order_id TEXT NOT NULL,
                amount REAL NOT NULL CHECK(amount > 0),
                status TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (case_id)
                    REFERENCES customer_cases(case_id),
                FOREIGN KEY (order_id)
                    REFERENCES orders(order_id)
            );

            CREATE TABLE IF NOT EXISTS audit_logs (
                log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                case_id TEXT,
                event_type TEXT NOT NULL,
                details TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS approval_queue (
                approval_id INTEGER PRIMARY KEY AUTOINCREMENT,
                case_id TEXT NOT NULL UNIQUE,
                status TEXT NOT NULL DEFAULT 'PENDING',
                reviewer_notes TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                reviewed_at TEXT,
                FOREIGN KEY (case_id)
                    REFERENCES customer_cases(case_id)
            );
            """
        )


def log_event(case_id, event_type, details):
    """Record an event for audit and debugging."""

    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO audit_logs (case_id, event_type, details)
            VALUES (?, ?, ?)
            """,
            (case_id, event_type, details),
        )
