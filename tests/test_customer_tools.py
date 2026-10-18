
from database.db import initialize_database
from database.seed import seed_database

from tools.customer_tools import (
    lookup_order,
    search_refund_policy,
    get_customer_history,
    check_fraud_risk,
    create_refund,
)


def setup_module():
    seed_database()


def test_lookup_order():
    result = lookup_order("ORD1001")

    assert result["success"] is True
    assert result["order"]["amount"] == 799.0


def test_unknown_order():
    result = lookup_order("ORD9999")

    assert result["success"] is False


def test_refund_policy():
    result = search_refund_policy()

    assert result["success"] is True
    assert len(result["policies"]) >= 1


def test_customer_history():
    result = get_customer_history("CUST001")

    assert result["success"] is True
    assert len(result["cases"]) >= 1


def test_customer_order_mismatch_is_flagged():
    result = check_fraud_risk("CUST002", "ORD1001")

    assert result["risk_level"] == "HIGH"


def test_refund_requires_approval():
    result = create_refund(
        case_id="CASE001",
        order_id="ORD1001",
        customer_id="CUST001",
        amount=799.0,
    )

    assert result["success"] is False
    assert "approved" in result["error"].lower()


def test_invalid_refund_amount():
    result = create_refund(
        case_id="CASE001",
        order_id="ORD1001",
        customer_id="CUST001",
        amount=-10.0,
    )

    assert result["success"] is False
