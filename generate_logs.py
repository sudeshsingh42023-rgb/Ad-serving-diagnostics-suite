"""
Generates synthetic ad-call logs simulating OpenRTB bid request/response
traffic and VAST tag responses across multiple partners, with realistic
integration errors injected so the diagnostics suite has something to find.

Run:
    python src/generate_logs.py
Writes:
    data/ad_call_logs.jsonl
"""

import json
import random
import uuid
from datetime import datetime, timedelta, timezone

random.seed(42)

PARTNERS = [
    {"id": "partner_alpha", "name": "Alpha Media Network", "error_bias": 0.05},
    {"id": "partner_bravo", "name": "Bravo Publishing Group", "error_bias": 0.28},
    {"id": "partner_charlie", "name": "Charlie Video Platform", "error_bias": 0.15},
    {"id": "partner_delta", "name": "Delta Mobile Apps", "error_bias": 0.35},
    {"id": "partner_echo", "name": "Echo News Network", "error_bias": 0.08},
]

REQUIRED_BID_REQUEST_FIELDS = ["id", "imp", "site_or_app", "at", "tmax"]
REQUIRED_IMP_FIELDS = ["id", "bidfloor", "banner_or_video"]

VAST_MACROS = ["[CACHEBUSTING]", "[ERRORCODE]", "[CLICK_URL]", "[IMPRESSION_URL]"]


def make_bid_request(partner_id, force_error=None):
    req_id = str(uuid.uuid4())
    imp_id = str(uuid.uuid4())[:8]

    request = {
        "id": req_id,
        "imp": [
            {
                "id": imp_id,
                "bidfloor": round(random.uniform(0.5, 8.0), 2),
                "banner_or_video": random.choice(["banner", "video"]),
            }
        ],
        "site_or_app": {"id": partner_id, "domain": f"{partner_id}.example.com"},
        "at": 1,
        "tmax": random.choice([100, 120, 150, 200]),
    }

    if force_error == "missing_field":
        # Drop a required top-level field to simulate a malformed request
        drop = random.choice(["at", "tmax", "site_or_app"])
        request.pop(drop, None)
    elif force_error == "missing_imp_field":
        drop = random.choice(["bidfloor", "banner_or_video"])
        request["imp"][0].pop(drop, None)

    return request


def make_bid_response(request, partner, force_error=None):
    latency_ms = max(10, int(random.gauss(90, 30)))
    if force_error == "latency_spike":
        latency_ms = random.randint(400, 1200)

    price = round(random.uniform(0.6, 9.0), 2)
    vast_valid = True
    # In a healthy response, the ad server substitutes the macro with a
    # real cachebusting value before the tag is served.
    resolved_cachebuster = str(random.randint(10**9, 10**10 - 1))
    vast_xml = (
        f'<VAST version="3.0"><Ad id="{uuid.uuid4().hex[:6]}">'
        f'<InLine><Impression><![CDATA[https://track.example.com/imp?ts={resolved_cachebuster}]]>'
        f'</Impression><Creatives></Creatives></InLine></Ad></VAST>'
    )

    if force_error == "malformed_vast":
        # Break the XML (unclosed tag) to simulate a bad VAST wrapper
        vast_xml = vast_xml.replace("</VAST>", "")
        vast_valid = False
    elif force_error == "unresolved_macro":
        # Simulate a macro that never got substituted at serve time
        vast_xml = vast_xml.replace(resolved_cachebuster, "[CACHEBUSTING]")
        vast_valid = "unresolved_macro"

    response = {
        "request_id": request.get("id", "UNKNOWN"),
        "partner_id": partner["id"],
        "price": price,
        "latency_ms": latency_ms,
        "vast_xml": vast_xml if request.get("imp", [{}])[0].get("banner_or_video") == "video" else None,
        "timestamp": None,  # filled in by caller
        "injected_error": force_error,
    }
    return response


def generate(n_events=1200, days_back=7):
    now = datetime.now(timezone.utc)
    events = []

    for _ in range(n_events):
        partner = random.choice(PARTNERS)
        ts = now - timedelta(
            days=random.uniform(0, days_back),
            hours=random.uniform(0, 24),
        )

        # Decide whether this event gets an injected error, weighted by partner's error_bias
        roll = random.random()
        force_error = None
        if roll < partner["error_bias"]:
            force_error = random.choice(
                ["missing_field", "missing_imp_field", "malformed_vast", "unresolved_macro", "latency_spike"]
            )

        req_error = force_error if force_error in ("missing_field", "missing_imp_field") else None
        resp_error = force_error if force_error in ("malformed_vast", "unresolved_macro", "latency_spike") else None

        request = make_bid_request(partner["id"], force_error=req_error)
        response = make_bid_response(request, partner, force_error=resp_error)
        response["timestamp"] = ts.isoformat()

        events.append({"request": request, "response": response, "partner_name": partner["name"]})

    events.sort(key=lambda e: e["response"]["timestamp"])
    return events


if __name__ == "__main__":
    import os
    _root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    events = generate()
    with open(os.path.join(_root, "data", "ad_call_logs.jsonl"), "w") as f:
        for e in events:
            f.write(json.dumps(e) + "\n")
    print(f"Wrote {len(events)} ad-call events to data/ad_call_logs.jsonl")
