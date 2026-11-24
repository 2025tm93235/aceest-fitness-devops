# SonarQube report: ACEest Fitness & Gym

Generated 2026-11-24 10:54 UTC from http://localhost:9000 (project key `aceest-fitness-devops`).

## Quality Gate: **PASSED**

| Condition | Actual | Threshold | Status |
| --- | --- | --- | --- |
| new_coverage | 100.0 | LT 80 | OK |
| new_duplicated_lines_density | 0.0 | GT 3 | OK |
| new_violations | 0 | GT 0 | OK |

## Measures

| Metric | Value |
| --- | --- |
| Lines of code | 1689 |
| Coverage (%) | 99.5 |
| Duplicated lines (%) | 0.0 |
| Bugs | 0 |
| Vulnerabilities | 2 |
| Code smells | 0 |
| Security hotspots | 0 |
| Reliability rating | A |
| Security rating | E |
| Maintainability rating | A |
| Unit tests | 207 |

## Open issues (2)

| Severity | Type | Rule | File | Line | Message |
| --- | --- | --- | --- | --- | --- |
| BLOCKER | VULNERABILITY | python:S6437 | aceest/auth.py | 23 | Revoke and change this password, as it is compromised. |
| CRITICAL | VULNERABILITY | python:S4502 | aceest/__init__.py | 22 | Make sure disabling CSRF protection is safe here. |