from __future__ import annotations

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from api.schemas import GeminiRequest
from api.services import (
    gemini_prediction_response,
    metadata_response,
    prediction_response,
)
from dashboard.data_loader import COFFEE_TYPES, FEATURE_VERSIONS


app = FastAPI(
    title="Coffee Model Dashboard API",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/metadata")
def get_metadata():
    try:
        return metadata_response()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/api/prediction")
def get_prediction(
    coffee_type: str = Query(..., pattern="^(robusta|arabica)$"),
    feature_version: str = Query(..., pattern="^(original|generated|selected)$"),
    date: str = Query(...),
    model_key: str | None = Query(None),
):
    if coffee_type not in COFFEE_TYPES or feature_version not in FEATURE_VERSIONS:
        raise HTTPException(status_code=400, detail="Unsupported coffee type or feature version")
    try:
        return prediction_response(coffee_type, feature_version, date, model_key)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/gemini")
def post_gemini(request: GeminiRequest):
    if request.coffee_type not in COFFEE_TYPES or request.feature_version not in FEATURE_VERSIONS:
        raise HTTPException(status_code=400, detail="Unsupported coffee type or feature version")
    try:
        return gemini_prediction_response(
            request.coffee_type,
            request.feature_version,
            request.date,
            request.model_key,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
