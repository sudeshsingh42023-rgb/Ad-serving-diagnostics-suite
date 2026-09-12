# Ad Serving Partner Integration Diagnostics Suite

A diagnostics and reporting tool that mirrors the core day-to-day work of a
**Partner Solutions Engineer** in ad tech: validating a partner's
programmatic (OpenRTB) and video (VAST) integrations, scoring their health,
and communicating findings to two very different audiences — engineers and
the partner's own (often non-technical) business team.

## Why this project

The Google Partner Solutions Engineer / gTech Ads role centers on:
- Troubleshooting partner integrations and performing **implementation reviews**
- Familiarity with the **ad serving industry** (OpenRTB, VAST, publisher/exchange integrations)
- **Data-driven** partner management
- Translating complex technical findings for a **non-technical audience**
- Client-side **web technologies** (HTML/CSS/JS/HTTP)

This project is a working (simplified) version of the internal tool a PSE
would actually want on the job when a partner says "our ads stopped
filling" or "our video ads won't play."

## What it does

1. **Simulates ad-call traffic** (`src/generate_logs.py`) — synthetic OpenRTB
   bid requests/responses and VAST video tags across 5 partners, with
   realistic integration errors injected at different rates per partner
   (missing required fields, malformed VAST XML, unresolved tracking
   macros, latency spikes).
2. **Validates each event** (`src/validators.py`) against a simplified
   OpenRTB/VAST spec — the same categories of checks used in a real
   implementation review.
3. **Scores integration health** (`src/health_score.py`) — rolls validation
   results into a 0–100 health score per partner per day, and ranks the
   top recurring failure modes per partner.
4. **Serves it via an API** (`src/api.py`, FastAPI) that a dashboard or any
   internal tool can consume.
5. **Renders a dashboard** (`dashboard/index.html`, HTML/JS/Chart.js) —
   a partner leaderboard and health-score trend chart.
6. **Generates a two-audience report** (`src/report_generator.py`) — one
   markdown file per partner with a plain-language summary and business
   impact estimate up top, and a technical error-code appendix at the
   bottom for engineering handoff. This is the piece that most directly
   demonstrates "convey complex technical concepts to a non-technical
   audience."

## Running it

```bash
pip install -r requirements.txt

cd src
python generate_logs.py        # writes ../data/ad_call_logs.jsonl
python health_score.py         # prints per-partner leaderboard, writes ../data/partner_summary.json
python report_generator.py partner_delta   # writes ../reports/partner_delta_review.md

uvicorn api:app --reload --port 8000
```

Then open `dashboard/index.html` in a browser (with the API running on
`localhost:8000`) to see the live leaderboard and trend chart.

Or with Docker:

```bash
docker build -t ad-diagnostics .
docker run -p 8000:8000 ad-diagnostics
```

## Example output

Partner leaderboard (from `health_score.py`):

```
Partner                  Avg Health  Events    Top Failure Modes
Delta Mobile Apps        73.0        253       LATENCY_CRITICAL(20), MISSING_REQUIRED_FIELD(17), MISSING_IMP_FIELD(13)
Bravo Publishing Group   73.3        245       LATENCY_CRITICAL(16), MISSING_REQUIRED_FIELD(14), UNRESOLVED_MACRO(7)
Charlie Video Platform   86.5        254       MISSING_IMP_FIELD(11), LATENCY_CRITICAL(10), UNRESOLVED_MACRO(6)
Echo News Network        94.6        208       MISSING_IMP_FIELD(7), MISSING_REQUIRED_FIELD(5), UNRESOLVED_MACRO(1)
Alpha Media Network      98.0        240       MISSING_REQUIRED_FIELD(4), MISSING_IMP_FIELD(1), LATENCY_CRITICAL(1)
```

Partner-facing report excerpt (`reports/partner_delta_review.md`):

> **Overall integration health score: 73.0/100**
>
> A meaningful share of ad responses are taking far too long, which is very
> likely timing out before the ad can render — this is actively costing
> revenue. Affects an estimated 7.9% of your traffic (20 of 253 requests
> reviewed).

## Project structure

```
ad-serving-diagnostics-suite/
├── src/
│   ├── generate_logs.py     # synthetic OpenRTB/VAST traffic generator
│   ├── validators.py        # OpenRTB + VAST + latency validation rules
│   ├── health_score.py      # per-partner/day scoring + leaderboard
│   ├── report_generator.py  # two-audience partner report generator
│   └── api.py                # FastAPI service
├── dashboard/
│   └── index.html            # HTML/JS/Chart.js dashboard
├── data/                      # generated logs + summaries (gitignored in practice)
├── reports/                   # generated partner review reports
├── requirements.txt
└── Dockerfile
```

## Possible extensions

- Swap the synthetic generator for a real log ingestion path (e.g., reading
  from BigQuery or Cloud Logging).
- Add Slack/email delivery of the partner report.
- Add a "regression" check that diffs today's failure modes against last
  week's to catch newly-introduced partner-side bugs.
