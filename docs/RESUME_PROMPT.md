# RESUME PROMPT - Quantum Stone Capital Hybrid Project

**Paste this entire file into a new Claude chat, then say:**
**"Continue this project."**

---

## Instructions for the Assistant Reading This

You are resuming an in-progress project. Before doing anything:

1. Read this entire file
2. Read the files it references (`docs/CONTEXT.md`,
   `docs/HYBRID_ARCHITECTURE.md`, `docs/STEP_LOG.md` tail,
   `PROJECT_STATE.md`)
3. Confirm to the user: "I see we are at Delivery X, next is Y. Ready
   to continue?"
4. Follow every rule in section 7 of this file
5. Do NOT re-explain the project; the user knows it. Just continue.

---

## 1. What This Project Is

**Quantum Stone Capital (QSC)** is a live trading system with its own
pipeline (feeds -> microstructure -> strategy_selector -> debate ->
jurors -> TradeProposal -> account_router -> broker_pool -> dashboard).

**HFT_Brain** is a second, independent trading system with a different
pipeline (regime_tagger -> 42 Python strategies -> 3-round bot debate ->
3-jury verdict). It was built separately.

**The hybrid goal:** run BOTH pipelines in parallel. A new
**ConsensusArbiter** reconciles their outputs. QSC's execution stack
remains authoritative for routing and broker calls.

**Constraint:** QSC is NOT rewritten. Its existing code stays as-is,
except ~10 lines added to `core/main_brain_v2.py` (Delivery 5b).

---

## 2. Where We Are Right Now

- **Last completed delivery:** 5a-1 (strategies_py infrastructure)
- **Next delivery:** 5a-2 (order_flow strategies)
- **Total tests passing:** ~450
- **Commit cadence:** manual commit per delivery; checkpoint every 5th
- **Baseline before hybrid:** 259 tests (Phase 13 checkpoint)

See `PROJECT_STATE.md` for the live snapshot and `docs/STEP_LOG.md`
tail for the exact last step number.

---

## 3. Architecture Summary

See `docs/HYBRID_ARCHITECTURE.md` for the full design. Key points:

- **Beta Brain** lives entirely in `beta_brain/` — isolated namespace
- **Python strategies** live in `strategies_py/` — 42 files in 6
  categories (order_flow, liquidity, supply_demand, ict_smc, patterns,
  ml_adaptive, volatility, trend)
- **QSC's YAML strategies** in `strategies/` are untouched
- **Arbiter** in `consensus/arbiter.py` decides final direction + size
- **Trainer** in `training/trainer.py` runs nightly: reads
  `logs/consensus/YYYY-MM-DD.jsonl`, computes strategy weights +
  arbiter thresholds, writes `data/models/brain/YYYY-MM-DD/`,
  updates `data/models/brain/current.json`, archives the JSONL

### Arbiter Decision Matrix

| QSC Brain | Beta Brain | Consensus  | Size |
|-----------|------------|------------|------|
| LONG      | BUY        | BOTH_AGREE | 1.0x |
| SHORT     | SELL       | BOTH_AGREE | 1.0x |
| LONG      | HOLD       | QSC_ONLY   | 0.5x |
| SHORT     | HOLD       | QSC_ONLY   | 0.5x |
| HOLD      | BUY        | BETA_ONLY  | 0.5x |
| HOLD      | SELL       | BETA_ONLY  | 0.5x |
| LONG      | SELL       | DISAGREE   | 0.0x |
| SHORT     | BUY        | DISAGREE   | 0.0x |
| HOLD      | HOLD       | BOTH_HOLD  | 0.0x |

---

## 4. Locked Decisions

Full list in `docs/CONTEXT.md`. Summary:

- Q13: Flat test layout — `tests/test_*.py`, no subfolders
- Q14: JSONL daily rotation to `logs/consensus/archive/`
- Q16: Training target = strategy weights + arbiter thresholds
- Q17: Manual trainer invocation (`scripts/train_brain_daily.py`)
- Q18: Always write versioned state folder, even no-op days
- Q19: Archive-only + manual rollback (`--rollback YYYY-MM-DD`)
- Q20: `current.json` pointer at `data/models/brain/current.json`
- Encoding: data files UTF-8 **without BOM** (use
  `[System.IO.File]::WriteAllText` with `UTF8Encoding($false)`)
- Git: manual per delivery, checkpoint every 5th

---

## 5. Directory Additions (hybrid)

    beta_brain/         Beta Brain (signal, debate, jury, guard, etc.)
    strategies_py/      42 Python strategies (in progress)
    consensus/          Arbiter + audit logger
    training/           Daily trainer + rollback
    backtest/           Beta backtest runners (future)
    knowledge/          62-book knowledge base (future)
    config/consensus.yaml              Arbiter config
    config/strategy_regime_filters.yaml  Beta strategy filter (Q14)
    config/strategy_tiers.yaml          Beta strategy tiers
    logs/consensus/     Active JSONL + archive/
    data/models/brain/  Versioned trained state + current.json

QSC's original folders (core/, brokers/, feeds/, microstructure/,
strategies/, ml/, dashboard/, jurors/, layers/, utils/, workers/) are
unchanged. See `docs/FILE_TREE.md` for the full tree.

---

## 6. What Comes Next

| Delivery | Scope | Files | Tests |
|----------|-------|-------|-------|
| 5a-2 | order_flow strategies | 8 + 8 tests | +8 |
| 5a-3 | liquidity + supply_demand | 10 + 10 tests | +10 |
| 5a-4 | ICT/SMC + patterns + ML + volatility + trend | ~19 + tests | +19 |
| 5b | BetaBrain + Arbiter + run_hybrid.py + main_brain patch + dashboard patch **CHECKPOINT** | ~6 + 25 tests | +25 |

After 5b, run: `.\scripts\checkpoint.ps1 -Label "Hybrid deliveries 1-5 complete"`.

---

## 7. Rules the Assistant Must Follow

1. **Every file is created via terminal paste** — no "open VS Code
   and paste this." Use `@'...'@ | Out-File` blocks.
2. **Data files (JSON/JSONL/YAML) are UTF-8 without BOM.** Use
   `[System.IO.File]::WriteAllText($path, $content, [System.Text.UTF8Encoding]::new($false))`.
   Never `Out-File -Encoding utf8` for those.
3. **Tests are flat** in `tests/test_*.py`. Run with `pytest tests/ -q`.
4. **Every delivery ends with:**
   - `pytest tests/ -q` — must be green
   - `.\scripts\log_step.ps1 -Message "..."`
   - `python scripts/update_file_tree.py`
   - `git add . && git commit -m "..." && git push`
5. **Checkpoint every 5th delivery** via `.\scripts\checkpoint.ps1`.
6. **No QSC file is deleted or rewritten** except the 2 files listed in
   HYBRID_ARCHITECTURE section 7 (`core/main_brain_v2.py` and
   `dashboard/state.py`) in Delivery 5b.
7. **Naming:** QSC Brain / Beta Brain / Arbiter / Trainer — never
   "brain" alone.
8. **Windows/PowerShell context:** LF->CRLF warnings from git are
   benign; ignore them.
9. **Tests:** always report count and PASS/FAIL. If a test fails,
   diagnose root cause and propose either source fix or test fix —
   never silently adjust.

---

## 8. Deep Reference Index

| File | Purpose |
|------|---------|
| `docs/STEP_LOG.md` | Full chronological history (Steps 001–current) |
| `PROJECT_STATE.md` | Live snapshot (commit, tests, checkpoint) |
| `docs/CONTEXT.md` | Locked Q&A decisions + conventions |
| `docs/HYBRID_ARCHITECTURE.md` | System design (updated) |
| `docs/BETA_BRAIN.md` | Beta Brain delivery log |
| `docs/PHASE_LOG.md` | Phase-level narrative (Phases 1–13, Hybrid) |
| `docs/FILE_TREE.md` | Auto-generated full file tree |
| `KNOWLEDGE_BASE.md` | Project knowledge notes (root) |
| `README.md` | Project overview (root) |

---

## 9. Recovery Scenarios

**If a paste failed mid-execution:**
Re-run the entire paste block. Blocks are idempotent — overwriting
files with `-Force` is safe.

**If tests are red after a paste:**
Run `pytest tests/ -q -x` to stop at first failure. Paste the failure
output. Diagnose before proceeding.

**If chat hits a limit:**
Paste this file (`docs/RESUME_PROMPT.md`) into a new chat and say
"continue this project." Do not paste any chat history.

**If you need to rollback training:**
`python scripts/train_brain_daily.py --rollback YYYY-MM-DD`

**If tests are green but a delivery looks wrong:**
Re-run the delivery paste. Nothing prevents re-running.

---

## 10. Style Guide (for consistency)

- Terminal paste blocks start with a header comment
  `# ==== DELIVERY N - title ====`
- Numbered `Write-Host "[X/Y] ..."` progress markers
- End with verification: `pytest tests/ -q` and a summary
- Every paste ends with the 4 finalize commands printed as
  `Write-Host` lines the user can copy
