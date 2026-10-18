
# ResolveAI — Autonomous Customer Resolution Agent

ResolveAI is an AI-powered customer support resolution platform built using
LangGraph, Groq, FastAPI, SQLite, and Streamlit.

It investigates synthetic customer cases, checks order information and refund
policies, evaluates risk, recommends a resolution, and routes eligible cases
to a human approval queue.

> This is an educational demo using synthetic data. Refunds are simulated
> database records only. No real payments are processed.

## Features

- **AI investigation:** Uses Groq to generate an investigation summary.
- **Agent workflow:** Uses LangGraph to coordinate investigation and decisions.
- **Customer and order lookup:** Retrieves information from SQLite.
- **Refund policy checks:** Validates return-window and amount limits.
- **Risk checks:** Flags cases that fail eligibility requirements.
- **Human-in-the-loop review:** Supports approval and rejection of pending cases.
- **Audit logging:** Records workflow and reviewer events.
- **REST API:** Exposes endpoints through FastAPI.
- **Web dashboard:** Provides an interactive Streamlit interface.
- **Automated tests:** Tests core tools, workflow, and API behavior.

## Technology Stack

- Python
- LangGraph
- Groq API
- FastAPI
- Streamlit
- SQLite
- Pydantic
- Pytest

## Project Structure

```text
ResolveAI/
├── agent/
│   ├── state.py
│   └── workflow.py
├── api/
│   └── main.py
├── database/
│   ├── db.py
│   └── seed.py
├── tests/
│   ├── test_setup.py
│   ├── test_customer_tools.py
│   ├── test_workflow.py
│   └── test_api.py
├── tools/
│   └── customer_tools.py
├── app.py
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

## Setup Instructions

### 1. Clone the repository

```bash
git clone YOUR_GITHUB_REPOSITORY_URL
cd ResolveAI
```

### 2. Create a virtual environment

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```powershell
python -m pip install -r requirements.txt
```

### 4. Configure the Groq API key

Create a `.env` file in the project root:

```env
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=llama-3.3-70b-versatile
```

Replace the placeholder with your own API key. Never commit `.env` to GitHub.

If you do not configure the key, the workflow may use its fallback AI-analysis message, depending on the implementation.

### 5. Initialize synthetic demo data

```powershell
python -c "from database.seed import seed_database; seed_database()"
```

### 6. Start the API

```powershell
uvicorn api.main:app --reload
```

API base URL:

```text
http://127.0.0.1:8000
```

Interactive API documentation:

```text
http://127.0.0.1:8000/docs
```

### 7. Start the dashboard

Open a second terminal in the project root:

```powershell
streamlit run app.py
```

## Main API Endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/health` | Check API health |
| GET | `/cases` | List customer cases |
| GET | `/cases/{case_id}` | Get a specific case |
| POST | `/resolve` | Run the resolution workflow |
| GET | `/approvals` | List pending approvals |
| POST | `/approvals/{case_id}/approve` | Approve an eligible case |
| POST | `/approvals/{case_id}/reject` | Reject a pending case |

## Run Tests

```powershell
python -m pytest tests -v
```

## Workflow

1. Load the customer case.
2. Investigate the order, customer history, and refund policy.
3. Check risk and eligibility rules.
4. Generate an AI investigation summary.
5. Record the workflow decision and audit events.
6. Route eligible cases for human review.
7. Create a simulated refund record only after approval and validation.

## Safety and Limitations

- Uses synthetic demonstration data.
- Does not integrate with a payment gateway.
- AI output is advisory; deterministic rules control eligibility.
- The approval workflow is a portfolio prototype, not a production authorization system.
- Production use would require authentication, role-based access control,
  stronger transactional guarantees, monitoring, and security testing.

## Future Improvements

- Authentication and role-based access control
- Better monitoring and observability
- More comprehensive integration tests
- Deployment with managed secrets and a hosted database
- Additional customer-support tools and evaluation metrics

## Author

Dhruv Ajay Sharma

GitHub: https://github.com/Dhruv200207
