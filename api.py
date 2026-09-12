"""
FastAPI service exposing partner integration health data to the
dashboard. Run with:

    uvicorn api:app --reload --port 8000

Endpoints:
    GET /api/partners          -> summary row per partner (for the table/leaderboard)
    GET /api/partners/{id}/trend -> daily health score trend for one partner
    GET /api/health             -> service healthcheck
"""

from collections import defaultdict

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from health_score import load_events, score_events, partner_summary

app = FastAPI(title="Ad Serving Partner Diagnostics API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Loaded once at startup; regenerate data/ad_call_logs.jsonl and restart
# the service to refresh with new synthetic data.
_events = load_events()
_daily_scores, _failure_modes, _partner_names = score_events(_events)
_summary = partner_summary(_daily_scores, _failure_modes, _partner_names)


@app.get("/api/health")
def health():
    return {"status": "ok", "events_loaded": len(_events)}


@app.get("/api/partners")
def get_partners():
    return _summary


@app.get("/api/partners/{partner_id}/trend")
def get_partner_trend(partner_id: str):
    trend = []
    for (pid, date_str), stats in sorted(_daily_scores.items(), key=lambda kv: kv[0][1]):
        if pid == partner_id:
            trend.append({"date": date_str, **stats})
    if not trend:
        raise HTTPException(status_code=404, detail=f"No data for partner_id '{partner_id}'")
    return trend


@app.get("/api/partners/{partner_id}/failures")
def get_partner_failures(partner_id: str):
    if partner_id not in _failure_modes:
        raise HTTPException(status_code=404, detail=f"No data for partner_id '{partner_id}'")
    return dict(_failure_modes[partner_id])
