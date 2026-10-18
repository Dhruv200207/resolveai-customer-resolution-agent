
import streamlit as st
import requests

API_URL = "http://127.0.0.1:8000"

# --------------------------------------------------
# PAGE CONFIGURATION
# --------------------------------------------------

st.set_page_config(
    page_title="ResolveAI Dashboard",
    page_icon="🤖",
    layout="wide",
)

st.title("🤖 ResolveAI")
st.caption("AI-Powered Customer Resolution Platform")

st.info(
    "Demo mode: ResolveAI uses synthetic customer data. "
    "No real payments or refunds are processed."
)

# --------------------------------------------------
# CHECK FASTAPI CONNECTION
# --------------------------------------------------

try:
    health_response = requests.get(
        f"{API_URL}/health",
        timeout=5,
    )
    health_response.raise_for_status()
    api_is_running = True

except requests.RequestException:
    api_is_running = False

if not api_is_running:
    st.error(
        "FastAPI is not running. Open another terminal "
        "and run: uvicorn api.main:app --reload"
    )
    st.stop()

st.success("FastAPI connected successfully.")

# --------------------------------------------------
# LOAD CUSTOMER CASES
# --------------------------------------------------

st.header("📋 Customer Cases")

try:
    response = requests.get(
        f"{API_URL}/cases",
        timeout=10,
    )
    response.raise_for_status()
    cases = response.json().get("cases", [])

except requests.RequestException as exc:
    st.error(f"Could not load customer cases: {exc}")
    st.stop()

if not cases:
    st.warning("No customer cases found in the database.")
    st.stop()

case_options = {
    f'{case["case_id"]} — {case["issue"]}': case["case_id"]
    for case in cases
}

selected_label = st.selectbox(
    "Select a customer case",
    options=list(case_options.keys()),
)

selected_case_id = case_options[selected_label]

selected_case = next(
    case for case in cases
    if case["case_id"] == selected_case_id
)

col1, col2, col3 = st.columns(3)

col1.metric("Case ID", selected_case["case_id"])
col2.metric("Current Status", selected_case["status"])
col3.metric(
    "Risk Level",
    selected_case.get("risk_level") or "Unknown",
)

st.write("**Customer ID:**", selected_case["customer_id"])
st.write("**Order ID:**", selected_case["order_id"])
st.write("**Issue:**", selected_case["issue"])
st.write("**Decision:**", selected_case.get("decision") or "Not decided")

# --------------------------------------------------
# RUN AI INVESTIGATION
# --------------------------------------------------

st.divider()
st.header("🔍 AI Investigation")

if st.button(
    "Run AI Investigation",
    type="primary",
    use_container_width=True,
):
    try:
        with st.spinner("Investigating the customer case..."):
            result_response = requests.post(
                f"{API_URL}/resolve",
                json={"case_id": selected_case_id},
                timeout=120,
            )
            result_response.raise_for_status()

            result_payload = result_response.json()
            st.session_state["last_result"] = result_payload["result"]
            st.session_state["last_case_id"] = selected_case_id

    except requests.RequestException as exc:
        st.error(f"Investigation request failed: {exc}")

# Display investigation result for the selected case
result = st.session_state.get("last_result")
result_case_id = st.session_state.get("last_case_id")

if result and result_case_id == selected_case_id:
    st.subheader("🧠 Investigation Results")

    decision = result.get("decision", "UNKNOWN")
    reason = result.get("reason", "No explanation returned.")

    st.write("**Final Decision:**", decision)
    st.write("**Reason:**", reason)

    if result.get("ai_analysis"):
        st.write("**AI Analysis:**")
        st.write(result["ai_analysis"])

    if result.get("error"):
        st.warning(result["error"])

    with st.expander("View complete investigation result"):
        st.json(result)

# --------------------------------------------------
# HUMAN APPROVAL QUEUE
# --------------------------------------------------

st.divider()
st.header("🧑‍💼 Human Approval Queue")

st.write(
    "Review pending cases. Approval is subject to backend "
    "eligibility checks. Refund records are simulated only."
)

try:
    approval_response = requests.get(
        f"{API_URL}/approvals",
        timeout=10,
    )
    approval_response.raise_for_status()

    approvals = approval_response.json().get("approvals", [])

except requests.RequestException as exc:
    st.error(f"Could not load approval queue: {exc}")
    approvals = []

if not approvals:
    st.info(
        "No pending approvals currently. Run an investigation "
        "for a case that is eligible for human review."
    )

else:
    for approval in approvals:
        case_id = approval["case_id"]

        with st.expander(
            f'{case_id} — {approval.get("issue", "Customer case")}'
        ):
            st.write("**Customer ID:**", approval.get("customer_id"))
            st.write("**Order ID:**", approval.get("order_id"))
            st.write("**Issue:**", approval.get("issue"))
            st.write("**Risk Level:**", approval.get("risk_level"))
            st.write("**Decision:**", approval.get("decision"))
            st.write("**Status:**", approval.get("approval_status"))

            notes = st.text_input(
                "Review notes",
                key=f"review_notes_{case_id}",
                placeholder="Enter your review notes",
                max_chars=500,
            )

            approve_col, reject_col = st.columns(2)

            with approve_col:
                if st.button(
                    "✅ Approve",
                    key=f"approve_{case_id}",
                    use_container_width=True,
                ):
                    try:
                        with st.spinner("Validating approval..."):
                            action_response = requests.post(
                                f"{API_URL}/approvals/{case_id}/approve",
                                json={"notes": notes},
                                timeout=30,
                            )

                        if action_response.ok:
                            st.success("Case approved.")
                            st.json(action_response.json())
                            st.rerun()
                        else:
                            try:
                                detail = action_response.json().get(
                                    "detail",
                                    action_response.text,
                                )
                            except ValueError:
                                detail = action_response.text

                            st.error(f"Approval failed: {detail}")

                    except requests.RequestException as exc:
                        st.error(f"Approval request failed: {exc}")

            with reject_col:
                if st.button(
                    "❌ Reject",
                    key=f"reject_{case_id}",
                    use_container_width=True,
                ):
                    try:
                        action_response = requests.post(
                            f"{API_URL}/approvals/{case_id}/reject",
                            json={"notes": notes},
                            timeout=30,
                        )

                        if action_response.ok:
                            st.success("Case rejected.")
                            st.json(action_response.json())
                            st.rerun()
                        else:
                            try:
                                detail = action_response.json().get(
                                    "detail",
                                    action_response.text,
                                )
                            except ValueError:
                                detail = action_response.text

                            st.error(f"Rejection failed: {detail}")

                    except requests.RequestException as exc:
                        st.error(f"Rejection request failed: {exc}")

# --------------------------------------------------
# REFRESH AND FOOTER
# --------------------------------------------------

st.divider()

if st.button("🔄 Refresh Dashboard"):
    st.rerun()

st.caption(
    "ResolveAI | LangGraph • Groq AI • FastAPI • SQLite • Streamlit"
)
