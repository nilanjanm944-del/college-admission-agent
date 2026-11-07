"""
app.py — FastAPI REST service for the College Admission Agent
Exposes two endpoints:
  POST /predict   — run the full agent workflow and return a prediction
  GET  /health    — liveness probe
"""

from __future__ import annotations

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, field_validator

from agent import ApplicantProfile, AdmissionResult, run_agent

# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------
app = FastAPI(
    title="College Admission Agent",
    description=(
        "Predicts the probability of graduate school admission using a "
        "watsonx.ai online deployment endpoint. "
        "The underlying model was trained on the Graduate Admissions dataset."
    ),
    version="1.0.0",
    contact={
        "name": "College Admission Agent",
        "url": "https://github.com/nilanjanm944-del/college-admission-agent",
    },
    license_info={"name": "MIT"},
)


# ---------------------------------------------------------------------------
# Request / response schemas
# ---------------------------------------------------------------------------
class PredictRequest(BaseModel):
    GRE_Score: int = Field(..., ge=260, le=340, description="GRE score (260–340)")
    TOEFL_Score: int = Field(..., ge=0, le=120, description="TOEFL score (0–120)")
    University_Rating: int = Field(..., ge=1, le=5, description="University rating (1–5)")
    SOP: float = Field(..., ge=1.0, le=5.0, description="Statement of Purpose strength (1–5)")
    LOR: float = Field(..., ge=1.0, le=5.0, description="Letter of Recommendation strength (1–5)")
    CGPA: float = Field(..., ge=0.0, le=10.0, description="Undergraduate CGPA (0–10)")
    Research: int = Field(..., ge=0, le=1, description="Research experience: 0 = No, 1 = Yes")

    @field_validator("Research")
    @classmethod
    def research_must_be_binary(cls, v: int) -> int:
        if v not in (0, 1):
            raise ValueError("Research must be 0 or 1")
        return v

    model_config = {
        "json_schema_extra": {
            "example": {
                "GRE_Score": 320,
                "TOEFL_Score": 110,
                "University_Rating": 4,
                "SOP": 4.5,
                "LOR": 4.0,
                "CGPA": 8.5,
                "Research": 1,
            }
        }
    }


class PredictResponse(BaseModel):
    chance_of_admit: float = Field(..., description="Predicted probability of admission (0–1)")
    recommendation: str = Field(..., description="Human-readable recommendation")
    profile: dict = Field(..., description="Echo of the submitted applicant profile")


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.get("/health", tags=["Ops"])
def health() -> dict:
    """Liveness probe — returns 200 OK when the service is running."""
    return {"status": "ok"}


@app.post("/predict", response_model=PredictResponse, tags=["Prediction"])
def predict(body: PredictRequest) -> PredictResponse:
    """Run the college admission agent workflow.

    Calls the watsonx.ai deployment endpoint and returns a structured
    admission-chance prediction together with a human-readable recommendation.
    """
    profile = ApplicantProfile(
        GRE_Score=body.GRE_Score,
        TOEFL_Score=body.TOEFL_Score,
        University_Rating=body.University_Rating,
        SOP=body.SOP,
        LOR=body.LOR,
        CGPA=body.CGPA,
        Research=body.Research,
    )

    try:
        result: AdmissionResult = run_agent(profile)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Upstream watsonx.ai error: {exc}") from exc

    return PredictResponse(
        chance_of_admit=result.chance_of_admit,
        recommendation=result.recommendation,
        profile=result.profile,
    )
