"""
Aggregates per-event validation results into a per-partner, per-day
"integration health score" (0-100) plus a ranked list of the most
common failure modes — the numbers a PSE would actually bring into a
partner review call.
"""

import json
import os
from collections import defaultdict
from datetime import datetime

from validators import validate_event

SEVERITY_WEIGHTS = {"critical": 10, "warning": 3, "info": 0}

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_LOG_PATH = os.path.join(_PROJECT_ROOT, "data", "ad_call_logs.jsonl")


def load_events(path=None):
    path = path or DEFAULT_LOG_PATH
    events = []
    with open(path) as f:
        for line in f:
            events.append(json.loads(line))
    return events


def score_events(events):
    """
    Returns:
      daily_scores: {(partner_id, date_str): {"score": float, "total": int, "healthy": int}}
      failure_modes: {partner_id: {issue_code: count}}
      partner_names: {partner_id: name}
    """
    daily_penalty = defaultdict(float)
    daily_total = defaultdict(int)
    daily_healthy = defaultdict(int)
    failure_modes = defaultdict(lambda: defaultdict(int))
    partner_names = {}

    for event in events:
        partner_id = event["response"]["partner_id"]
        partner_names[partner_id] = event.get("partner_name", partner_id)
        date_str = event["response"]["timestamp"][:10]
        key = (partner_id, date_str)

        result = validate_event(event)
        daily_total[key] += 1
        if result.is_healthy:
            daily_healthy[key] += 1

        for issue in result.issues:
            daily_penalty[key] += SEVERITY_WEIGHTS.get(issue.severity, 0)
            failure_modes[partner_id][issue.code] += 1

    daily_scores = {}
    for key, total in daily_total.items():
        # Normalize penalty by volume so high-traffic partners aren't
        # unfairly punished just for having more events.
        max_possible_penalty = total * SEVERITY_WEIGHTS["critical"]
        penalty = daily_penalty[key]
        score = 100.0 if max_possible_penalty == 0 else max(0.0, 100.0 * (1 - penalty / max_possible_penalty))
        daily_scores[key] = {
            "score": round(score, 1),
            "total_events": total,
            "healthy_events": daily_healthy[key],
        }

    return daily_scores, failure_modes, partner_names


def partner_summary(daily_scores, failure_modes, partner_names):
    """Rolls daily scores up into one row per partner for the dashboard."""
    per_partner_scores = defaultdict(list)
    per_partner_events = defaultdict(int)
    for (partner_id, _date), stats in daily_scores.items():
        per_partner_scores[partner_id].append(stats["score"])
        per_partner_events[partner_id] += stats["total_events"]

    summary = []
    for partner_id, scores in per_partner_scores.items():
        top_failures = sorted(failure_modes[partner_id].items(), key=lambda kv: -kv[1])[:3]
        summary.append(
            {
                "partner_id": partner_id,
                "partner_name": partner_names.get(partner_id, partner_id),
                "avg_health_score": round(sum(scores) / len(scores), 1),
                "total_events": per_partner_events[partner_id],
                "top_failure_modes": [{"code": code, "count": count} for code, count in top_failures],
            }
        )
    summary.sort(key=lambda r: r["avg_health_score"])
    return summary


if __name__ == "__main__":
    events = load_events()
    daily_scores, failure_modes, partner_names = score_events(events)
    summary = partner_summary(daily_scores, failure_modes, partner_names)

    print(f"{'Partner':<25}{'Avg Health':<12}{'Events':<10}Top Failure Modes")
    for row in summary:
        failures = ", ".join(f"{f['code']}({f['count']})" for f in row["top_failure_modes"]) or "none"
        print(f"{row['partner_name']:<25}{row['avg_health_score']:<12}{row['total_events']:<10}{failures}")

    with open(os.path.join(_PROJECT_ROOT, "data", "partner_summary.json"), "w") as f:
        json.dump(summary, f, indent=2)
    print("\nWrote data/partner_summary.json")
