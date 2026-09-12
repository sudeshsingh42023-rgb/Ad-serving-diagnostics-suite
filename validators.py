"""
Validates OpenRTB bid requests/responses and VAST tags against a
simplified spec, returning a structured list of integration issues.
This is the core "implementation review" logic a Partner Solutions
Engineer would run when a partner reports serving problems.
"""

import re
from dataclasses import dataclass, field
from typing import List, Optional

REQUIRED_REQUEST_FIELDS = ["id", "imp", "site_or_app", "at", "tmax"]
REQUIRED_IMP_FIELDS = ["id", "bidfloor", "banner_or_video"]
LATENCY_WARN_MS = 200
LATENCY_CRITICAL_MS = 400


@dataclass
class Issue:
    code: str
    severity: str  # "info" | "warning" | "critical"
    message: str


@dataclass
class ValidationResult:
    request_id: str
    partner_id: str
    issues: List[Issue] = field(default_factory=list)

    @property
    def is_healthy(self) -> bool:
        return not any(i.severity in ("warning", "critical") for i in self.issues)


def validate_bid_request(request: dict) -> List[Issue]:
    issues = []
    for field_name in REQUIRED_REQUEST_FIELDS:
        if field_name not in request:
            issues.append(
                Issue(
                    code="MISSING_REQUIRED_FIELD",
                    severity="critical",
                    message=f"Bid request is missing required field '{field_name}'",
                )
            )

    for imp in request.get("imp", []):
        for field_name in REQUIRED_IMP_FIELDS:
            if field_name not in imp:
                issues.append(
                    Issue(
                        code="MISSING_IMP_FIELD",
                        severity="critical",
                        message=f"Impression object missing required field '{field_name}'",
                    )
                )
    if "imp" not in request or not request.get("imp"):
        issues.append(
            Issue(code="NO_IMPRESSIONS", severity="critical", message="Bid request has no impression objects")
        )
    return issues


def validate_vast(vast_xml: Optional[str]) -> List[Issue]:
    issues = []
    if vast_xml is None:
        return issues  # not a video impression, nothing to check

    if not vast_xml.strip().startswith("<VAST"):
        issues.append(Issue(code="VAST_MALFORMED", severity="critical", message="VAST response does not start with a <VAST> root element"))
        return issues

    if "</VAST>" not in vast_xml:
        issues.append(Issue(code="VAST_MALFORMED", severity="critical", message="VAST XML is unclosed / truncated (missing </VAST>)"))

    # Check for macros that appear to have never been substituted at serve time.
    # A real macro like [CACHEBUSTING] left literally in the tracking URL means
    # the ad server failed to fire the substitution step.
    unresolved = re.findall(r"\[[A-Z_]+\]", vast_xml)
    if unresolved:
        issues.append(
            Issue(
                code="UNRESOLVED_MACRO",
                severity="warning",
                message=f"VAST contains unresolved macro(s): {', '.join(sorted(set(unresolved)))}",
            )
        )
    return issues


def validate_latency(latency_ms: int) -> List[Issue]:
    issues = []
    if latency_ms >= LATENCY_CRITICAL_MS:
        issues.append(
            Issue(code="LATENCY_CRITICAL", severity="critical", message=f"Response latency {latency_ms}ms exceeds critical threshold ({LATENCY_CRITICAL_MS}ms)")
        )
    elif latency_ms >= LATENCY_WARN_MS:
        issues.append(
            Issue(code="LATENCY_WARNING", severity="warning", message=f"Response latency {latency_ms}ms exceeds warning threshold ({LATENCY_WARN_MS}ms)")
        )
    return issues


def validate_event(event: dict) -> ValidationResult:
    request = event["request"]
    response = event["response"]

    result = ValidationResult(
        request_id=request.get("id", "UNKNOWN"),
        partner_id=response.get("partner_id", "UNKNOWN"),
    )
    result.issues.extend(validate_bid_request(request))
    result.issues.extend(validate_vast(response.get("vast_xml")))
    result.issues.extend(validate_latency(response.get("latency_ms", 0)))
    return result
