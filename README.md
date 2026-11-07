# College Admission Agent

A **FastAPI + FastMCP** service that predicts graduate school admission chances
using a **watsonx.ai** online deployment endpoint.

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│  Client (curl / browser / MCP host)                     │
└────────────────┬────────────────────────────────────────┘
                 │  HTTP POST /predict
                 ▼
┌─────────────────────────────────────────────────────────┐
│  app.py  — FastAPI REST service                         │
│   • validates request with Pydantic                     │
│   • calls agent.run_agent()                             │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│  agent.py  — Workflow orchestrator                      │
│   • builds WML payload                                  │
│   • exchanges IBM Cloud API key → IAM token             │
│   • calls watsonx.ai deployment endpoint                │
│   • maps prediction → recommendation                    │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│  mcp_tool.py  — FastMCP server                          │
│   • tool: predict_admission_chance                      │
│   • also callable by any MCP-compatible host            │
└─────────────────────────────────────────────────────────┘
```

---

## Files

| File | Purpose |
|---|---|
| `app.py` | FastAPI REST service (`POST /predict`, `GET /health`) |
| `agent.py` | Core workflow: IAM auth → WML call → recommendation |
| `mcp_tool.py` | FastMCP server exposing `predict_admission_chance` |
| `requirements.txt` | Python runtime dependencies |

---

## Prerequisites

- Python ≥ 3.10
- An **IBM Cloud API key** with access to the Watson Machine Learning instance
  that owns deployment `01a1abb2-7435-728c-99e1-4c7d2fb32f02`

---

## Quick start

### 1 — Clone and install

```bash
git clone https://github.com/nilanjanm944-del/college-admission-agent.git
cd college-admission-agent
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

### 2 — Set environment variables

```bash
# Required
export IBM_CLOUD_API_KEY="<your-ibm-cloud-api-key>"

# Optional — override the default deployment URL
export WATSONX_DEPLOYMENT_URL="https://au-syd.ml.cloud.ibm.com/ml/v4/deployments/01a1abb2-7435-728c-99e1-4c7d2fb32f02/predictions?version=2021-05-01"
```

On Windows (PowerShell):

```powershell
$env:IBM_CLOUD_API_KEY = "<your-ibm-cloud-api-key>"
```

### 3 — Run the FastAPI service

```bash
uvicorn app:app --reload
```

The service starts on `http://127.0.0.1:8000`.  
Interactive docs: `http://127.0.0.1:8000/docs`

### 4 — Run the FastMCP server (standalone)

```bash
python mcp_tool.py
```

---

## API reference

### `GET /health`

Liveness probe.

```json
{ "status": "ok" }
```

---

### `POST /predict`

**Request body**

```json
{
  "gre_score": 320,
  "toefl_score": 110,
  "university_rating": 4,
  "sop": 4.5,
  "lor": 4.0,
  "cgpa": 8.5,
  "research": 1
}
```

| Field | Type | Range | Description |
|---|---|---|---|
| `gre_score` | float | 260–340 | GRE total score |
| `toefl_score` | float | 0–120 | TOEFL score |
| `university_rating` | int | 1–5 | Undergraduate institution rating |
| `sop` | float | 1.0–5.0 | Statement of Purpose strength |
| `lor` | float | 1.0–5.0 | Letter of Recommendation strength |
| `cgpa` | float | 0.0–10.0 | Undergraduate CGPA |
| `research` | int | 0 or 1 | Research experience (1 = Yes) |

**Response body**

```json
{
  "chance_of_admit": 0.87,
  "recommendation": "Strong candidate — very likely to be admitted.",
  "profile": {
    "gre_score": 320,
    "toefl_score": 110,
    "university_rating": 4,
    "sop": 4.5,
    "lor": 4.0,
    "cgpa": 8.5,
    "research": 1
  }
}
```

**Example with curl**

```bash
curl -X POST http://127.0.0.1:8000/predict \
  -H "Content-Type: application/json" \
  -d '{
    "gre_score": 320,
    "toefl_score": 110,
    "university_rating": 4,
    "sop": 4.5,
    "lor": 4.0,
    "cgpa": 8.5,
    "research": 1
  }'
```

---

## Recommendation thresholds

| Chance of Admit | Recommendation |
|---|---|
| ≥ 0.80 | Strong candidate — very likely to be admitted. |
| ≥ 0.60 | Good candidate — admission is probable. |
| ≥ 0.40 | Moderate candidate — strengthening profile is advised. |
| < 0.40 | Weak candidate — consider improving scores or research. |

---

## Watsonx.ai deployment details

| Property | Value |
|---|---|
| Region | `au-syd` (Sydney) |
| Deployment ID | `01a1abb2-7435-728c-99e1-4c7d2fb32f02` |
| API version | `2021-05-01` |
| Auth | IBM Cloud IAM (API key → bearer token) |

---

## License

MIT
