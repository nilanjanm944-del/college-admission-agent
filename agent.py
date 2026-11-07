"""
agent.py — College Admission Agent workflow
Orchestrates the admission-chance prediction using the FastMCP tool and
returns a structured recommendation for the applicant.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, asdict

import requests
from dotenv import load_dotenv

load_dotenv()


# ---------------------------------------------------------------------------
# Input / output models (plain dataclasses — no external deps required)
# ---------------------------------------------------------------------------
@dataclass
class ApplicantProfile:
    GRE_Score: int
    TOEFL_Score: int
    University_Rating: int
    SOP: float
    LOR: float
    CGPA: float
    Research: int  # 0 or 1


@dataclass
class AdmissionResult:
    chance_of_admit: float
    recommendation: str
    profile: dict
    raw_response: dict | None = None


# ---------------------------------------------------------------------------
# Recommendation thresholds
# ---------------------------------------------------------------------------
_THRESHOLDS = [
    (0.80, "Strong candidate — very likely to be admitted."),
    (0.60, "Good candidate — admission is probable with a competitive application."),
    (0.40, "Moderate candidate — admission is possible; strengthening your profile is advised."),
    (0.00, "Weak candidate — consider improving GRE/TOEFL scores, CGPA, or research experience."),
]


def _recommendation(chance: float) -> str:
    for threshold, message in _THRESHOLDS:
        if chance >= threshold:
            return message
    return "Unable to determine — please verify the input values."


# ---------------------------------------------------------------------------
# Deployment helpers (reused from mcp_tool to avoid circular import)
# ---------------------------------------------------------------------------
DEPLOYMENT_URL = os.getenv(
    "WATSONX_DEPLOYMENT_URL",
    "https://au-syd.ml.cloud.ibm.com/ml/v4/deployments/"
    "01a1abb2-7435-728c-99e1-4c7d2fb32f02/predictions?version=2021-05-01",
)


def _get_iam_token() -> str:
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


def _call_deployment(profile: ApplicantProfile) -> dict:
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
                "values": [[
                    profile.GRE_Score,
                    profile.TOEFL_Score,
                    profile.University_Rating,
                    profile.SOP,
                    profile.LOR,
                    profile.CGPA,
                    profile.Research,
                ]],
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
    return resp.json()


# ---------------------------------------------------------------------------
# Public agent entry-point
# ---------------------------------------------------------------------------
def run_agent(profile: ApplicantProfile) -> AdmissionResult:
    """Run the full admission-prediction workflow for *profile*.

    Steps:
      1. Call the watsonx.ai deployment endpoint.
      2. Extract the predicted chance of admit (first value in predictions[0].values[0]).
      3. Generate a human-readable recommendation.
      4. Return a structured ``AdmissionResult``.
    """
    raw = _call_deployment(profile)

    predictions = raw.get("predictions", [{}])
    values = predictions[0].get("values", [[None]])[0]
    chance = float(values[0]) if values and values[0] is not None else 0.0

    return AdmissionResult(
        chance_of_admit=chance,
        recommendation=_recommendation(chance),
        profile=asdict(profile),
        raw_response=raw,
    )
