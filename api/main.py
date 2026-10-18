
import json
from datetime import date, datetime
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from agent.workflow import process_case
from database.db import get_connection, log_event
from tools.customer_tools import create_refund

app = FastAPI(
    title="ResolveAI API",
    description="Customer resolution agent using synthetic demo data.",
    version="0.3.0",
)


class ResolutionRequest(BaseModel):
    case_id: str = Field(min_length=1, max_length=50)


class ReviewRequest(BaseModel):
    notes: str = Field(default="", max_length=500)


@app.get("/")
def home():
    return {
        "project": "ResolveAI",
        "message": "Customer Resolution API is running.",
        "mode": "synthetic_demo",
    }


@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "resolveai-api"}


@app.get("/cases")
def list_cases():
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT case_id, customer_id, order_id, issue,
                   status, risk_level, decision
            FROM customer_cases
            ORDER BY case_id
            """
        ).fetchall()

    return {"cases": [dict(row) for row in rows]}


@app.get("/cases/{case_id}")
def get_case(case_id: str):
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT case_id, customer_id, order_id, issue,
                   status, risk_level, decision
            FROM customer_cases
            WHERE case_id = ?
            """,
            (case_id,),
        ).fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail="Case not found")

    return {"case": dict(row)}


@app.post("/resolve")
def resolve_case(request: ResolutionRequest):
    with get_connection() as conn:
        exists = conn.execute(
            "SELECT case_id FROM customer_cases WHERE case_id = ?",
            (request.case_id,),
        ).fetchone()

    if exists is None:
        raise HTTPException(status_code=404, detail="Case not found")

    try:
        result = process_case(request.case_id)
        return {"success": True, "result": result}
    except Exception as exc:
        print(f"ResolveAI workflow error: {exc}")
        raise HTTPException(
            status_code=500,
            detail="The resolution workflow failed. Check server logs.",
        ) from exc


@app.get("/approvals")
def list_approvals():
    """List cases awaiting human review."""
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT q.case_id, q.status AS approval_status,
                   q.reviewer_notes, q.created_at,
                   c.customer_id, c.order_id, c.issue,
                   c.status AS case_status, c.risk_level, c.decision
            FROM approval_queue q
            JOIN customer_cases c ON c.case_id = q.case_id
            WHERE q.status = 'PENDING'
            ORDER BY q.created_at
            """
        ).fetchall()

    return {"approvals": [dict(row) for row in rows]}


@app.post("/approvals/{case_id}/approve")
def approve_case(case_id: str, request: ReviewRequest):
    """Approve an eligible case and create a simulated refund record."""
    with get_connection() as conn:
        case = conn.execute(
            """
            SELECT c.case_id, c.customer_id, c.order_id,
                   c.status, c.risk_level, c.decision,
                   o.amount, o.order_status, o.delivery_date,
                   o.customer_id AS order_customer_id
            FROM customer_cases c
            JOIN orders o ON o.order_id = c.order_id
            WHERE c.case_id = ?
            """,
            (case_id,),
        ).fetchone()

        queue = conn.execute(
            "SELECT status FROM approval_queue WHERE case_id = ?",
            (case_id,),
        ).fetchone()

        policy = conn.execute(
            """
            SELECT return_window_days, max_auto_refund
            FROM refund_policies
            WHERE active = 1
            ORDER BY policy_id
            LIMIT 1
            """
        ).fetchone()

        existing_refund = conn.execute(
            "SELECT refund_id FROM refunds WHERE case_id = ?",
            (case_id,),
        ).fetchone()

    if case is None:
        raise HTTPException(status_code=404, detail="Case not found")

    if queue is None or queue["status"] != "PENDING":
        raise HTTPException(
            status_code=409,
            detail="This case has no pending approval.",
        )

    if existing_refund is not None:
        raise HTTPException(
            status_code=409,
            detail="A refund record already exists for this case.",
        )

    if (
        case["status"] != "PENDING_APPROVAL"
        or case["decision"] != "PENDING_APPROVAL"
        or case["risk_level"] != "LOW"
    ):
        raise HTTPException(
            status_code=400,
            detail="The case has not passed the required eligibility checks.",
        )

    if (
        case["order_status"] != "DELIVERED"
        or case["customer_id"] != case["order_customer_id"]
    ):
        raise HTTPException(
            status_code=400,
            detail="Order delivery or customer ownership validation failed.",
        )

    if not policy or not case["delivery_date"]:
        raise HTTPException(
            status_code=400,
            detail="An active policy or delivery date is unavailable.",
        )

    try:
        delivery_date = date.fromisoformat(case["delivery_date"])
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail="The order delivery date is invalid.",
        ) from exc

    days_since_delivery = (date.today() - delivery_date).days

    if days_since_delivery < 0 or days_since_delivery > policy["return_window_days"]:
        raise HTTPException(
            status_code=400,
            detail="The order is outside the allowed return window.",
        )

    amount = float(case["amount"])

    if amount > float(policy["max_auto_refund"]):
        raise HTTPException(
            status_code=400,
            detail="The amount exceeds the configured refund policy limit.",
        )

    # create_refund performs additional database validations.
    try:
        refund = create_refund(
            case_id=case_id,
            order_id=case["order_id"],
            customer_id=case["customer_id"],
            amount=amount,
        )
    except Exception as exc:
        print(f"Simulated refund creation error: {exc}")
        raise HTTPException(
            status_code=400,
            detail="Simulated refund could not be created. Check the policy and case.",
        ) from exc

    with get_connection() as conn:
        conn.execute(
            """
            UPDATE approval_queue
            SET status = 'APPROVED',
                reviewer_notes = ?,
                reviewed_at = ?
            WHERE case_id = ? AND status = 'PENDING'
            """,
            (request.notes, datetime.utcnow().isoformat(), case_id),
        )

        conn.execute(
            """
            UPDATE customer_cases
            SET status = 'APPROVED'
            WHERE case_id = ? AND status = 'PENDING_APPROVAL'
            """,
            (case_id,),
        )

        conn.execute(
            """
            INSERT INTO audit_logs (case_id, event_type, details)
            VALUES (?, ?, ?)
            """,
            (
                case_id,
                "HUMAN_APPROVAL",
                json.dumps({
                    "reviewer_notes": request.notes,
                    "refund": "simulated database record only",
                }),
            ),
        )

    return {
        "success": True,
        "case_id": case_id,
        "decision": "APPROVED",
        "refund": refund,
        "message": "Simulated refund record created. No real payment was made.",
    }


@app.post("/approvals/{case_id}/reject")
def reject_case(case_id: str, request: ReviewRequest):
    """Reject a pending case and record the review."""
    with get_connection() as conn:
        queue = conn.execute(
            "SELECT status FROM approval_queue WHERE case_id = ?",
            (case_id,),
        ).fetchone()

        case = conn.execute(
            "SELECT status FROM customer_cases WHERE case_id = ?",
            (case_id,),
        ).fetchone()

        if case is None:
            raise HTTPException(status_code=404, detail="Case not found")

        if queue is None or queue["status"] != "PENDING":
            raise HTTPException(
                status_code=409,
                detail="This case has no pending approval.",
            )

        conn.execute(
            """
            UPDATE approval_queue
            SET status = 'REJECTED',
                reviewer_notes = ?,
                reviewed_at = ?
            WHERE case_id = ? AND status = 'PENDING'
            """,
            (request.notes, datetime.utcnow().isoformat(), case_id),
        )

        conn.execute(
            """
            UPDATE customer_cases
            SET status = 'REJECTED'
            WHERE case_id = ? AND status = 'PENDING_APPROVAL'
            """,
            (case_id,),
        )

        conn.execute(
            """
            INSERT INTO audit_logs (case_id, event_type, details)
            VALUES (?, ?, ?)
            """,
            (
                case_id,
                "HUMAN_REJECTION",
                json.dumps({"reviewer_notes": request.notes}),
            ),
        )

    return {
        "success": True,
        "case_id": case_id,
        "decision": "REJECTED",
        "message": "Case rejected and review recorded.",
    }
