#!/usr/bin/env python3
"""Export a SonarQube project report to Markdown (stdlib only, Python 3.9+).

Usage:
    SONAR_TOKEN=<token> python3 scripts/sonar_report.py \
        --url http://localhost:9000 --project aceest-fitness-devops \
        --output docs/sonarqube-report.md
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone

METRICS = {
    "ncloc": "Lines of code",
    "coverage": "Coverage (%)",
    "duplicated_lines_density": "Duplicated lines (%)",
    "bugs": "Bugs",
    "vulnerabilities": "Vulnerabilities",
    "code_smells": "Code smells",
    "security_hotspots": "Security hotspots",
    "reliability_rating": "Reliability rating",
    "security_rating": "Security rating",
    "sqale_rating": "Maintainability rating",
    "tests": "Unit tests",
}
RATINGS = {"1.0": "A", "2.0": "B", "3.0": "C", "4.0": "D", "5.0": "E"}


def get(base: str, path: str, params: dict[str, str], token: str) -> dict:
    url = f"{base.rstrip('/')}{path}?{urllib.parse.urlencode(params)}"
    request = urllib.request.Request(url)  # noqa: S310 - URL given by the operator
    auth = base64.b64encode(f"{token}:".encode()).decode()
    request.add_header("Authorization", f"Basic {auth}")
    with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310
        return json.loads(response.read())


def build_report(base: str, project: str, token: str) -> str:
    gate = get(base, "/api/qualitygates/project_status", {"projectKey": project}, token)
    measures = get(
        base,
        "/api/measures/component",
        {"component": project, "metricKeys": ",".join(METRICS)},
        token,
    )
    issues = get(
        base,
        "/api/issues/search",
        {"componentKeys": project, "resolved": "false", "ps": "100"},
        token,
    )

    status = gate["projectStatus"]["status"]
    values = {m["metric"]: m.get("value", "-") for m in measures["component"]["measures"]}
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    lines = [
        f"# SonarQube report: {measures['component'].get('name', project)}",
        "",
        f"Generated {now} from {base} (project key `{project}`).",
        "",
        f"## Quality Gate: **{'PASSED' if status == 'OK' else status}**",
        "",
        "| Condition | Actual | Threshold | Status |",
        "| --- | --- | --- | --- |",
    ]
    for condition in gate["projectStatus"].get("conditions", []):
        lines.append(
            f"| {condition['metricKey']} | {condition.get('actualValue', '-')} | "
            f"{condition.get('comparator', '')} {condition.get('errorThreshold', '')} | "
            f"{condition['status']} |"
        )
    lines += ["", "## Measures", "", "| Metric | Value |", "| --- | --- |"]
    for key, label in METRICS.items():
        value = values.get(key, "-")
        lines.append(f"| {label} | {RATINGS.get(value, value)} |")
    lines += ["", f"## Open issues ({issues.get('total', 0)})", ""]
    if issues.get("issues"):
        lines += ["| Severity | Type | Rule | File | Line | Message |", "| --- " * 6 + "|"]
        for issue in issues["issues"]:
            component = issue["component"].split(":", 1)[-1]
            lines.append(
                f"| {issue.get('severity', '')} | {issue.get('type', '')} | {issue['rule']} | "
                f"{component} | {issue.get('line', '')} | {issue['message']} |"
            )
    else:
        lines.append("No open issues.")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--url", default="http://localhost:9000")
    parser.add_argument("--project", default="aceest-fitness-devops")
    parser.add_argument("--output", default="docs/sonarqube-report.md")
    args = parser.parse_args()
    token = os.environ.get("SONAR_TOKEN")
    if not token:
        print("Set SONAR_TOKEN to a SonarQube user token.", file=sys.stderr)
        return 2
    report = build_report(args.url, args.project, token)
    with open(args.output, "w", encoding="utf-8") as handle:
        handle.write(report)
    print(f"Wrote {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
