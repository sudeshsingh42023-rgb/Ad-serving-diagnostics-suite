# Integration Health Review — Delta Mobile Apps
_Generated 2026-09-12_

**Overall integration health score: 73.0/100**

Your integration is mostly healthy, but a few issues are worth fixing soon.

## What we found (plain-language summary)

- **A meaningful share of ad responses are taking far too long, which is very likely timing out before the ad can render — this is actively costing revenue.** Affects an estimated 7.9% of your traffic (20 of 253 requests reviewed).
- **Some of your ad requests are missing information our system needs to respond. This causes those requests to be dropped entirely, meaning lost impressions.** Affects an estimated 6.7% of your traffic (17 of 253 requests reviewed).
- **A portion of your requests don't fully describe the ad slot being requested, so we can't match a bid to them.** Affects an estimated 5.1% of your traffic (13 of 253 requests reviewed).

## Recommended next steps

1. Share the technical appendix below with your engineering team.
2. Prioritize any item marked critical in the appendix — these cause dropped requests or broken ads.
3. Re-run this review after fixes are deployed to confirm the health score has improved.

## Technical appendix (for engineering)

| Error Code | Occurrences |
|---|---|
| `LATENCY_CRITICAL` | 20 |
| `MISSING_REQUIRED_FIELD` | 17 |
| `MISSING_IMP_FIELD` | 13 |
| `UNRESOLVED_MACRO` | 11 |
| `VAST_MALFORMED` | 6 |