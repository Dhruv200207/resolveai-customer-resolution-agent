
from typing import Any, TypedDict


class ResolveAIState(TypedDict, total=False):
    case_id: str
    customer_id: str
    order_id: str
    issue: str

    order: dict[str, Any]
    policy: dict[str, Any]
    customer_history: dict[str, Any]
    risk: dict[str, Any]

    ai_analysis: str
    decision: str
    reason: str
    refund_amount: float

    tool_calls: list[str]
    error: str
    final_result: dict[str, Any]
