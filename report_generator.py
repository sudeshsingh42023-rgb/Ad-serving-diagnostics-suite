"""
Turns the technical validation output into two artifacts for two
different audiences — which is the actual skill being tested by the
"convey complex technical concepts to a non-technical audience"
qualification:

  1. A plain-language partner-facing summary (what's broken, business
     impact, what to fix) with no jargon.
  2. A technical appendix with exact error codes and counts for
     engineering handoff.

Run:
    python src/report_generator.py <partner_id>
"""

import os
import sys
import json
from datetime import datetime

from health_score import load_events, score_events, partner_summary

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

FRIENDLY_EXPLANATIONS = {
    "MISSING_REQUIRED_FIELD": (
        "Some of your ad requests are missing information our system needs to respond. "
        "This causes those requests to be dropped entirely, meaning lost impressions."
    ),
    "MISSING_IMP_FIELD": (
        "A portion of your requests don't fully describe the ad slot being requested, "
        "so we can't match a bid to them."
    ),
    "NO_IMPRESSIONS": (
        "Some requests are being sent with no ad slots attached at all — these can never be filled."
    ),
    "VAST_MALFORMED": (
        "Some video ad tags returned from your player are broken or incomplete, which can cause "
        "the video ad to fail to play, hurting viewability and revenue."
    ),
    "UNRESOLVED_MACRO": (
        "Tracking placeholders in some video ads aren't being replaced with real values before the "
        "ad plays. This under-reports your impression and click tracking."
    ),
    "LATENCY_WARNING": (
        "Some ad responses are slower than recommended, which can cause timeouts and lost fill rate."
    ),
    "LATENCY_CRITICAL": (
        "A meaningful share of ad responses are taking far too long, which is very likely timing out "
        "before the ad can render — this is actively costing revenue."
    ),
}


def business_impact_line(code, count, total_events):
    pct = round(100 * count / total_events, 1) if total_events else 0
    return f"Affects an estimated {pct}% of your traffic ({count} of {total_events} requests reviewed)."


def generate_partner_report(partner_id: str):
    events = load_events()
    daily_scores, failure_modes, partner_names = score_events(events)
    summary_rows = {row["partner_id"]: row for row in partner_summary(daily_scores, failure_modes, partner_names)}

    if partner_id not in summary_rows:
        print(f"No data found for partner_id '{partner_id}'")
        return

    row = summary_rows[partner_id]
    total_events = row["total_events"]
    partner_name = row["partner_name"]

    lines = []
    lines.append(f"# Integration Health Review — {partner_name}")
    lines.append(f"_Generated {datetime.now().strftime('%Y-%m-%d')}_\n")
    lines.append(f"**Overall integration health score: {row['avg_health_score']}/100**\n")

    if row["avg_health_score"] >= 90:
        lines.append("Your integration is in great shape. Below are a couple of minor items worth a look.\n")
    elif row["avg_health_score"] >= 70:
        lines.append("Your integration is mostly healthy, but a few issues are worth fixing soon.\n")
    else:
        lines.append("We found integration issues that are likely costing you meaningful revenue. Details below.\n")

    lines.append("## What we found (plain-language summary)\n")
    for f in row["top_failure_modes"]:
        explanation = FRIENDLY_EXPLANATIONS.get(f["code"], "An integration issue was detected.")
        lines.append(f"- **{explanation}** {business_impact_line(f['code'], f['count'], total_events)}")

    lines.append("\n## Recommended next steps\n")
    lines.append("1. Share the technical appendix below with your engineering team.")
    lines.append("2. Prioritize any item marked critical in the appendix — these cause dropped requests or broken ads.")
    lines.append("3. Re-run this review after fixes are deployed to confirm the health score has improved.\n")

    lines.append("## Technical appendix (for engineering)\n")
    lines.append("| Error Code | Occurrences |")
    lines.append("|---|---|")
    for code, count in sorted(failure_modes[partner_id].items(), key=lambda kv: -kv[1]):
        lines.append(f"| `{code}` | {count} |")

    report_text = "\n".join(lines)
    out_path = os.path.join(_PROJECT_ROOT, "reports", f"{partner_id}_review.md")
    with open(out_path, "w") as f:
        f.write(report_text)
    print(f"Wrote {out_path}")
    return report_text


if __name__ == "__main__":
    partner_id = sys.argv[1] if len(sys.argv) > 1 else "partner_delta"
    generate_partner_report(partner_id)
