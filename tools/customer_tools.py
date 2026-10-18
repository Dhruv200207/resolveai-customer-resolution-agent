
from database.db import get_connection, log_event


def lookup_order(order_id: str) -> dict:
    """Look up an order using its order ID."""

    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT o.*, c.name AS customer_name
            FROM orders o
            JOIN customers c
              ON o.customer_id = c.customer_id
            WHERE o.order_id = ?
            """,
            (order_id,),
        ).fetchone()

    if row is None:
        return {
            "success": False,
            "error": "Order not found.",
        }

    return {"success": True, "order": dict(row)}


def search_refund_policy() -> dict:
    """Retrieve the active refund policy."""

    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT policy_id, policy_name, description,
                   return_window_days, max_auto_refund
            FROM refund_policies
            WHERE active = 1
            ORDER BY policy_id
            """
        ).fetchall()

    return {
        "success": True,
        "policies": [dict(row) for row in rows],
    }


def get_customer_history(customer_id: str) -> dict:
    """Retrieve a customer's cases and refund history."""

    with get_connection() as conn:
        customer = conn.execute(
            """
            SELECT customer_id, name
            FROM customers
            WHERE customer_id = ?
            """,
            (customer_id,),
        ).fetchone()

        if customer is None:
            return {
                "success": False,
                "error": "Customer not found.",
            }

        cases = conn.execute(
            """
            SELECT case_id, order_id, issue, status,
                   risk_level, decision
            FROM customer_cases
            WHERE customer_id = ?
            ORDER BY created_at DESC
            """,
            (customer_id,),
        ).fetchall()

        refunds = conn.execute(
            """
            SELECT r.refund_id, r.order_id, r.amount, r.status
            FROM refunds r
            JOIN customer_cases cc
              ON r.case_id = cc.case_id
            WHERE cc.customer_id = ?
            ORDER BY r.created_at DESC
            """,
            (customer_id,),
        ).fetchall()

    return {
        "success": True,
        "customer": dict(customer),
        "cases": [dict(row) for row in cases],
        "refunds": [dict(row) for row in refunds],
        "previous_refund_count": len(refunds),
    }


def check_fraud_risk(
    customer_id: str,
    order_id: str,
) -> dict:
    """
    Identify simple risk signals.
    Signals require investigation; they do not prove fraud.
    """

    order_result = lookup_order(order_id)

    if not order_result["success"]:
        return {
            "success": False,
            "risk_level": "HIGH",
            "signals": ["Order could not be verified."],
        }

    order = order_result["order"]

    if order["customer_id"] != customer_id:
        return {
            "success": True,
            "risk_level": "HIGH",
            "signals": [
                "Customer ID does not match the order owner."
            ],
        }

    history = get_customer_history(customer_id)

    if not history["success"]:
        return {
            "success": False,
            "risk_level": "HIGH",
            "signals": ["Customer history could not be verified."],
        }

    signals = []

    if history["previous_refund_count"] >= 3:
        signals.append(
            "Multiple previous refund records require review."
        )

    if order["order_status"] != "DELIVERED":
        signals.append(
            "Order is not marked as delivered."
        )

    if signals:
        risk_level = "REVIEW"
    else:
        risk_level = "LOW"

    return {
        "success": True,
        "risk_level": risk_level,
        "signals": signals,
    }


def create_refund(
    case_id: str,
    order_id: str,
    customer_id: str,
    amount: float,
) -> dict:
    """
    Create a simulated refund only when strict checks pass.
    This function never calls a payment provider.
    """

    if amount <= 0:
        return {
            "success": False,
            "error": "Refund amount must be positive.",
        }

    with get_connection() as conn:
        case = conn.execute(
            """
            SELECT case_id, customer_id, order_id, status
            FROM customer_cases
            WHERE case_id = ?
            """,
            (case_id,),
        ).fetchone()

        if case is None:
            return {
                "success": False,
                "error": "Case not found.",
            }

        if (
            case["customer_id"] != customer_id
            or case["order_id"] != order_id
        ):
            return {
                "success": False,
                "error": "Case, customer and order do not match.",
            }

        existing = conn.execute(
            """
            SELECT refund_id, status
            FROM refunds
            WHERE case_id = ?
            """,
            (case_id,),
        ).fetchone()

        if existing is not None:
            return {
                "success": False,
                "error": "A refund record already exists for this case.",
            }

        if case["status"] != "APPROVED":
            return {
                "success": False,
                "error": "Case must be approved before refund creation.",
            }

        order = conn.execute(
            """
            SELECT amount, order_status, customer_id
            FROM orders
            WHERE order_id = ?
            """,
            (order_id,),
        ).fetchone()

        if order is None:
            return {
                "success": False,
                "error": "Order not found.",
            }

        if order["customer_id"] != customer_id:
            return {
                "success": False,
                "error": "Order ownership verification failed.",
            }

        if order["order_status"] != "DELIVERED":
            return {
                "success": False,
                "error": "Only delivered orders can be refunded.",
            }

        if amount > order["amount"]:
            return {
                "success": False,
                "error": "Refund cannot exceed the order amount.",
            }

        policy = conn.execute(
            """
            SELECT max_auto_refund
            FROM refund_policies
            WHERE active = 1
            ORDER BY policy_id
            LIMIT 1
            """
        ).fetchone()

        if policy is None or amount > policy["max_auto_refund"]:
            return {
                "success": False,
                "error": "Refund exceeds the automatic limit or policy is unavailable.",
            }

        risk = check_fraud_risk(customer_id, order_id)

        if not risk["success"] or risk["risk_level"] != "LOW":
            return {
                "success": False,
                "error": "Risk checks require further review.",
                "risk": risk,
            }

        # Insert and audit within one database transaction.
        conn.execute(
            """
            INSERT INTO refunds
                (case_id, order_id, amount, status)
            VALUES (?, ?, ?, ?)
            """,
            (case_id, order_id, amount, "SIMULATED"),
        )

        conn.execute(
            """
            INSERT INTO audit_logs
                (case_id, event_type, details)
            VALUES (?, ?, ?)
            """,
            (
                case_id,
                "SIMULATED_REFUND_CREATED",
                f"Demo refund of {amount:.2f} for {order_id}",
            ),
        )

    return {
        "success": True,
        "status": "SIMULATED",
        "case_id": case_id,
        "order_id": order_id,
        "amount": amount,
        "message": "Simulated refund record created successfully.",
    }
