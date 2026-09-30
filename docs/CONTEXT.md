# CONTEXT - Locked Design Decisions

**Purpose:** Immutable decision log. Any new chat reads this to
understand WHY the code is structured this way. If a decision here is
changed, add a new dated entry — never edit an old one.

**Last updated:** 2026-10-01

---

## Naming Convention (locked 2026-10-01)

| Term | Meaning |
|------|---------|
| QSC Brain | `core/main_brain_v2.py::MainBrainV2` (untouched) |
| Beta Brain | `beta_brain/beta_brain.py::BetaBrain` (new) |
| Arbiter | `consensus/arbiter.py::ConsensusArbiter` (new) |
| Trainer | `training/trainer.py::Trainer` (new) |
| Strategy (YAML) | A QSC strategy in `strategies/library.yaml` |
| Strategy (Python) | A Beta strategy in `strategies_py/` |
| Signal | `beta_brain/signal.py::Signal` (Beta's) or QSC's |

Never use "brain" alone in documentation or messages.

---

## Hybrid Goals (locked 2026-10-01)

- **Primary:** Run both pipelines in parallel. Both contribute to
  trading decisions. QSC's execution remains authoritative.
- **Non-negotiable:** QSC's existing code is not rewritten. Only
  two files gain small modifications in Delivery 5b:
  - `core/main_brain_v2.py` (+~10 lines)
  - `dashboard/state.py` (Decision dataclass +4 optional fields)
- **Toggleable:** `config/consensus.yaml: beta.enabled` can disable
  Beta Brain entirely without code changes.

---

## Locked Q&A Decisions

| ID | Question | Answer | Date |
|----|----------|--------|------|
| Q13 | Test file layout | Flat `tests/test_*.py` | 2026-10-01 |
| Q14 | Audit log rotation | JSONL daily, archive to `logs/consensus/archive/` | 2026-10-01 |
| Q16 | Training target | B — strategy weights + arbiter thresholds | 2026-10-01 |
| Q17 | Trainer trigger | A — manual (`scripts/train_brain_daily.py`) | 2026-10-01 |
| Q18 | No-op training day | A — always write versioned folder | 2026-10-01 |
| Q19 | Rollback policy | C — archive-only + manual CLI | 2026-10-01 |
| Q20 | Pointer file location | A — `data/models/brain/current.json` | 2026-10-01 |

---

## Encoding Policy (locked 2026-10-01)

Windows PowerShell 5.1's `Out-File -Encoding utf8` writes UTF-8 **with
BOM**, which breaks `json.load`. Rule:

- **Python source** (`.py`): BOM tolerated
- **Data files** (JSON, JSONL, YAML): UTF-8 **without BOM**

For PowerShell writes to data files:

    [System.IO.File]::WriteAllText($path, $content,
        [System.Text.UTF8Encoding]::new($false))

    [System.IO.File]::AppendAllText($path, $line + "`n",
        [System.Text.UTF8Encoding]::new($false))

Readers try `utf-8-sig` first, then `utf-8`, then `utf-16` (see
`consensus/audit.py::ConsensusAudit._read_lines`).

---

## Git Workflow (locked 2026-10-01)

- **Manual finalize** for deliveries D1–D4, D6–D9, ... (log_step,
  update_file_tree, add, commit, push)
- **Checkpoint** for D5, D10, D15, ... via `.\scripts\checkpoint.ps1`
  (adds: PROJECT_STATE refresh + pytest + phase log entry)
- LF→CRLF warnings on commit are benign — Windows Git normalization.
  Do not disable.

---

## Test Counts by Delivery (record only)

| Delivery | Tests | Commit |
|----------|-------|--------|
| Pre-hybrid baseline (Phase 13) | 259 | 3655bfb |
| D1 (skeleton) | 259 | f796fd9 |
| D2 (Beta 6 modules) | 325 | a07dcae |
| D3 (training package) | 360 | 0cdd885 |
| D3c (tz auto-detect) | 360 | 103370d |
| D3d (encoding-tolerant reader) | 360 | ea4e822 |
| D4a (Beta Signal + debate) | 392 | f6f1476 |
| D4b (Beta jury + verdict) | 427 | e9247be |
| D5a-1 (strategies_py infra) | ~450 | (pending) |
| D5a-2 (order_flow) | ~458 | — |
| D5a-3 (liquidity + sd) | ~468 | — |
| D5a-4 (rest + knowledge) | ~487 | — |
| D5b (integration) | ~512 | CHECKPOINT |

---

## Design Principles

1. **Isolation.** Beta Brain is self-contained. It does not import
   from QSC (`core/`, `strategies/`, `jurors/`) and does not reach
   into HFT_Brain's original namespace. Only Delivery 5b bridges.
2. **Idempotency.** Every paste block can be re-run without
   breaking. Files use `-Force`; folders use `-Force`.
3. **Single source of truth.** Beta's `Signal` lives in
   `beta_brain/signal.py`. QSC's Signal in
   `strategies/base_strategy.py`. Never cross.
4. **Conservative defaults.** PaperTrader checks SL before TP.
   Missing data returns `HOLD`, not a guess.
5. **Auditable.** Every arbiter decision is a JSONL record with both
   brains' inputs and the final size multiplier.

---

## Recovery Cheat Sheet

    # Chat died -> resume:
    #   paste docs/RESUME_PROMPT.md into new chat

    # Rollback training:
    python scripts/train_brain_daily.py --rollback 2026-09-30

    # List trained days:
    python scripts/train_brain_daily.py --list

    # Show current pointer + available days:
    python scripts/train_brain_daily.py --status

    # Run hybrid (once built):
    python scripts/run_hybrid.py --once

    # Run QSC alone (existing):
    python scripts/run_brain.py --once
