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

## ADR-008: Merkle tree promotes a lone node; it never duplicates

Status: Accepted

Decision: A level with an odd node count promotes the trailing node unchanged instead of duplicating it, and build_proof derives its siblings from the same level walk build_tree uses. legacy_root_hash() keeps the old construction only so anchors written before 2026-10-13 can still be re-verified.

Context: The original builder duplicated a trailing odd node (Bitcoin-style) and padded each level independently when building a proof. Two consequences:

- Different leaf sets collided: root([a,b,c]) equalled root([a,b,c,c]). A root no longer committed to exactly one batch, so an inclusion proof for a leaf of the shorter batch verified against the longer batch root.
- A promoted node could be paired with itself in a proof.

The module had no tests, so neither property was pinned. Found while adding inclusion proofs for the Phase C work.

Consequences:
- Anchors created from now on use the promotion scheme.
- perception/federated_verify.py accepts an old anchor and reports which scheme it used (merkle_scheme: promote | legacy_duplicate) instead of falsely calling a genuine old commitment tampered.
- invariants.py gains I5b_merkle_no_collision, and tests/test_merkle.py covers sizes 1-16, tampering, cross-root rejection, and domain separation.

## ADR-009: ember-lite is an installable library; inclusion proofs and receipts are engine-side

Status: Accepted

Decision: Add a pyproject.toml (package "perception" + top-level modules, console script ember-lite=ember_agent:main) so ember-signal can import the engine instead of shelling out. Add perception/inclusion_proof.py (per-block Merkle inclusion proof + anchor verification) and perception/receipts.py (Ed25519 receipt over an arbitrary response payload).

Context: ember-signal runs ember-lite in a subprocess because it "ships no pyproject/setup.py, so it cannot be pip install"ed" (its engine.py says so). Packaging removes that constraint without removing the subprocess path. Inclusion proofs let a holder of one block and an anchor root confirm inclusion offline; receipts let a client verify a response really came from the engine. Both build on the corrected Merkle tree (ADR-008).

Consequences:
- pip install -e . exposes perception and the top-level modules; the console script points at the existing ember_agent.main.
- inclusion_proof accepts either Merkle scheme and reports the scheme that matched an anchor.
- receipts never return a receipt claiming a signature they do not have: when cryptography is absent they return {"signed": false, "error": ...}.
- Tests: tests/test_inclusion_proof.py, tests/test_receipts.py; the engine contract test now also pins the new surfaces.
