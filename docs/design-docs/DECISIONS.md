# Design Decisions

## ADR-001: SQLite over Redis

Status: Accepted

Context: Cross-terminal bus on 2GB RAM.

Decision: SQLite with WAL mode.

Rationale:
| Criterion | SQLite | Redis |
|---|---|---|
| RAM | ~0 MB | 50-100 MB |
| Infra | Zero | Daemon |
| Precedent | Claude Bridge | Enterprise |

## ADR-002: Ed25519 over RSA

Status: Accepted

Decision: Ed25519 via cryptography library.

Rationale:
- 64-byte signatures
- NIST approved
- ATP Standard
- Pure Python fallback

## ADR-003: Transport != Orchestration

Status: Accepted

Decision: Bridge is transport only.

Rationale (Claude Bridge):
"A bridge is a transport, not an autonomous orchestrator."

## ADR-004: 6-Dimension Gate

Status: Accepted

Decision: Security + Performance + Evidence + Regression + Cost + Governance.

Rationale (Industry):
- Cerberus: Security + Performance + Cost
- 5-Dimension: + Groundedness + Safety
- BDP: PASS/REVIEW/BLOCKED

## ADR-005: Documentation-First Repo

Status: Accepted

Decision: AGENTS.md + docs/ + CI.

Rationale (agentic-engine):
"A single AGENTS.md works for humans and agents."

## ADR-006: Unknown is not a default

Status: Accepted

Decision: A release-gate dimension with no usable input reports `UNKNOWN`
(score 0, excluded from the weighted score). `SHIP` is impossible unless every
gate was actually evaluated.

Context: The gate previously defaulted every missing input to a passing value
(empty evidence graph scored 100, a missing perception report read as 0%, a
missing bridge produced a 0% error rate). A missing input could therefore read
as `SHIP`, which contradicts KPI #1 ("missing data = unknown, not default").

Consequences:
- The score weights only gates backed by real data.
- Any `UNKNOWN` gate downgrades the decision to `REVIEW` at best.
- `format_gate_report` shows an `❓ UNKNOWN` row with the reason.

## ADR-007: CI verifies evidence, not claims

Status: Accepted

Decision: `.github/workflows/evidence-verify.yml` runs
`scripts/verify_evidence.py`, which re-checks every committed signed bundle's
Ed25519 signature and the local evidence-chain hash chain, failing the build on
tamper. `tests.yml` runs the pytest suite across Python 3.11–3.13.

Context: "No record, no evidence" is only credible if CI enforces it. A CI
check turns the claim into something a machine verifies on every push.

## Related

- PRINCIPLES.md
