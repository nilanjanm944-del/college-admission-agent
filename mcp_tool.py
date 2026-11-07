"""
FastMCP tool: predict_admission_chance
Calls the watsonx.ai online deployment endpoint and returns the predicted
admission probability for a single applicant.
"""

import os
import requests
from dotenv import load_dotenv
from fastmcp import FastMCP

load_dotenv()

# ---------------------------------------------------------------------------
# MCP server instance
# ---------------------------------------------------------------------------
mcp = FastMCP("college-admission-agent")

# ---------------------------------------------------------------------------
# Watsonx.ai deployment endpoint (set via env or use the default below)
# ---------------------------------------------------------------------------
DEPLOYMENT_URL = os.getenv(
    "WATSONX_DEPLOYMENT_URL",
    "https://au-syd.ml.cloud.ibm.com/ml/v4/deployments/"
    "01a1abb2-7435-728c-99e1-4c7d2fb32f02/predictions?version=2021-05-01",
)


def _get_iam_token() -> str:
    """Exchange IBM Cloud API key for a short-lived IAM bearer token."""
    api_key = os.environ["IBM_API_KEY"]
    resp = requests.post(
        "https://iam.cloud.ibm.com/identity/token",
        data={
            "grant_type": "urn:ibm:params:oauth:grant-type:apikey",
            "apikey": api_key,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


# ---------------------------------------------------------------------------
# Tool definition
# ---------------------------------------------------------------------------
@mcp.tool()
def predict_admission_chance(
    GRE_Score: int,
    TOEFL_Score: int,
    University_Rating: int,
    SOP: float,
    LOR: float,
    CGPA: float,
    Research: int,
) -> dict:
    """Predict the probability of graduate school admission.

    Args:
        GRE_Score: GRE score (260–340).
        TOEFL_Score: TOEFL score (0–120).
        University_Rating: University rating (1–5).
        SOP: Statement of Purpose strength (1.0–5.0).
        LOR: Letter of Recommendation strength (1.0–5.0).
        CGPA: Undergraduate CGPA (0.0–10.0).
        Research: Research experience (0 = No, 1 = Yes).

    Returns:
        A dict with ``chance_of_admit`` (float 0–1) and the raw model response.
    """
    token = _get_iam_token()

    payload = {
        "input_data": [
            {
                "fields": [
                    "GRE Score",
                    "TOEFL Score",
                    "University Rating",
                    "SOP",
                    "LOR",
                    "CGPA",
                    "Research",
                ],
                "values": [[GRE_Score, TOEFL_Score, University_Rating, SOP, LOR, CGPA, Research]],
            }
        ]
    }

    resp = requests.post(
        DEPLOYMENT_URL,
        json=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        timeout=60,
    )
    resp.raise_for_status()
    result = resp.json()

    # Extract the scalar prediction value from the standard WML response shape
    predictions = result.get("predictions", [{}])
    values = predictions[0].get("values", [[None]])[0]
    chance = values[0] if values else None

    return {"chance_of_admit": chance, "raw_response": result}


if __name__ == "__main__":
    mcp.run()
