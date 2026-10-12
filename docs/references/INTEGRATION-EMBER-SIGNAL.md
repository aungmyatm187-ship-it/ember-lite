# Ember-Lite ↔ Ember-Signal Integration

Status: Analysis / plan. No cross-repo code has been written yet.

## What each repo actually is

| Repo | Reality (verified against the clone) |
|---|---|
| **ember-lite** (this repo) | Local-first Python CLI + perception engine. Layers P1–P6 under `perception/`. `perception/evidence_chain.py` is a hash-chained, Ed25519-signed append-only chain (SQLite). `perception/release_gate.py` is the 6-dimension gate. No web layer. |
| **ember-signal** | Minimal Flask app: `app.py`, `index.html`, `data.db`, `requirements.txt`, `ember-signal-evidence.json`. Two routes: `/` (dashboard) and `/api/signals` (top brands from `data.db` + the JSON evidence file). |

ember-signal's current evidence file (`ember-signal-evidence.json`) is a single
hand-written record, not a chain and not signed. ember-lite's `evidence/*.json`
bundles, by contrast, are Ed25519-signed (see `evidence/*.json.sig`).

## The honest integration seam

ember-lite is the **engine**; ember-signal is the **surface**. The clean seam is
a small HTTP boundary, not a merge of the two codebases:

| # | ember-signal adds | Reuses from ember-lite |
|---|---|---|
| 1 | `GET /api/evidence/chain` → chain summary + `verify_chain()` result | `perception/evidence_chain.py` |
| 2 | `GET /api/perceive` → latest perception report (JSON) | `perception/layer.py:perceive(save=False)` |
| 3 | `GET /health` → liveness for observers | — (gives ember-lite a real backend to observe) |

Reproduce ember-lite's tests and CLI must stay **local-first** (KPI #4). Any
integration should treat ember-signal as an optional remote observer, never as a
required dependency of the engine.

### Suggested shape (not yet implemented)

```python
# in ember-signal/app.py — thin wrapper over ember-lite
@app.route("/api/evidence/chain")
def evidence_chain():
    from perception.evidence_chain import get_chain_summary, verify_chain
    return jsonify({"summary": get_chain_summary(), "verify": verify_chain()})
```

Fuller proposal (subprocess or import-based adapter) was supplied in the
upgrade brief; pick one only after the two repos share a pinned version.

## Positioning (lumafoundry.live)

The studio frames two neighbours that match ember-lite's actual capabilities:

- **Selene Agents** (agent orchestration) ↔ ember-lite P3
  (`perception/orchestrator.py`) + the ember-signal dashboard as the UI.
- **Vanta Proof** (evidence-first AI governance) ↔ ember-lite P5
  (`release_gate.py`) + P6 (`governance.py`) + the signed evidence chain.

Neither mapping requires new claims. Both are already true of the code in this
repo. The one-line pitch for ember-signal:

> The evidence layer for terminal-native AI: perception, governance, and signed
> proof-of-operation, local-first.

## Open items before real fusion

1. Pin which ember-lite version ember-signal depends on (currently unversioned).
2. Decide adapter style (in-process import vs subprocess) — the engine must not
   take a hard dependency on Flask.
3. Do not put signing keys in ember-signal; signatures stay with ember-lite's
   `perception/keys/` (git-ignored).
4. The Railway backend referenced by committed evidence bundles is an external
   service; its availability is not something CI can currently assert.
