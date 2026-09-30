# Hybrid Architecture - Quantum Stone Capital + HFT_Brain

**Status:** In progress. Delivery 0 complete (continuity layer).
Next: 5a-1 (strategies_py infrastructure).
**Last updated:** 2026-10-01
**Owner:** Quantum Stone Capital

---

## 1. Naming Convention (locked)

| Term | Location |
|------|----------|
| QSC Brain | `core/main_brain_v2.py::MainBrainV2` (untouched) |
| Beta Brain | `beta_brain/beta_brain.py::BetaBrain` (new) |
| Arbiter | `consensus/arbiter.py::ConsensusArbiter` (new) |
| Trainer | `training/trainer.py::Trainer` (new) |

Never use "brain" alone.

---

## 2. Non-Negotiable Constraints

1. QSC's pipeline is NOT rewritten. Only 2 files gain ~10-15 lines
   each in Delivery 5b:
   - `core/main_brain_v2.py`
   - `dashboard/state.py`
2. No folder is replaced. All new work lives in new top-level
   packages.
3. Beta Brain is toggleable via `config/consensus.yaml`.
4. Every arbitration is logged to `logs/consensus/YYYY-MM-DD.jsonl`.

---

## 3. Top-Level Layout (hybrid additions)

    quantum-stone-capital/
    |-- core/           QSC Brain (existing, untouched)
    |-- brokers/        QSC (existing)
    |-- feeds/          QSC (existing)
    |-- microstructure/ QSC (existing)
    |-- strategies/     QSC YAML library (existing)
    |-- ml/             QSC ML stack (existing)
    |-- dashboard/      QSC dashboard (1 file gains 4 fields in 5b)
    |-- config/         + consensus.yaml, strategy_regime_filters.yaml,
    |                     strategy_tiers.yaml
    |-- beta_brain/     NEW - Beta Brain (signal, debate, jury, etc.)
    |-- strategies_py/  NEW - 42 Python strategies (in progress)
    |-- knowledge/      NEW - 62-book knowledge base (future)
    |-- consensus/      NEW - Arbiter + audit
    |-- training/       NEW - Daily trainer + rollback
    |-- backtest/       NEW - Beta backtest runners (future)
    |-- logs/consensus/ NEW - JSONL + archive/
    +-- data/models/brain/  NEW - versioned trained state + current.json

---

## 4. Pipelines

### QSC Brain (Alpha) — unchanged

    MarketContext
      -> microstructure.engine
      -> strategy_selector (strategies/library.yaml)
      -> core/debate_engine (QSC's own)
      -> QSC jurors (risk/strategy/execution)
      -> TradeProposal
      -> core.account_router -> brokers

Entry: `core.main_brain_v2.MainBrainV2.run(context) -> PipelineResult`

### Beta Brain

    MarketContext
      -> beta_brain.regime_tagger.tag()
      -> strategies_py.registry.run_all(candles, regime)
      -> beta_brain.debate.engine.run(signals)
      -> beta_brain.jury.verdict_engine.run(debate, mode, account_type)
      -> JuryVerdict

Entry: `beta_brain.beta_brain.BetaBrain.run(context) -> JuryVerdict`

### Arbiter (5b)

    Alpha PipelineResult + Beta JuryVerdict
      -> consensus.arbiter.ConsensusArbiter.decide(alpha, beta)
      -> ArbiterDecision { consensus, direction, size_multiplier, ... }
      -> applied to PipelineResult.metadata["arbiter"]

---

## 5. Arbiter Decision Matrix

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

Configurable via `config/consensus.yaml`.

---

## 6. Daily Training Lifecycle

    Live hours: QSC + Beta + Arbiter write to
                logs/consensus/YYYY-MM-DD.jsonl

    Trainer run (manual):
      1. Read today's JSONL (auto-detect newest active day)
      2. Read previous state via current.json pointer
      3. Compute new strategy weights + arbiter thresholds
      4. Write data/models/brain/YYYY-MM-DD/ (4 files)
      5. Update current.json
      6. Archive JSONL to logs/consensus/archive/YYYY-MM-DD.jsonl
      7. Print report

Training targets: Beta strategy weight multipliers + arbiter thresholds.

Rollback: `python scripts/train_brain_daily.py --rollback YYYY-MM-DD`.

---

## 7. Files Touched During Full Build

**NEW:** everything in `beta_brain/`, `strategies_py/`, `knowledge/`,
`consensus/`, `training/`, `backtest/`, `logs/consensus/`,
`data/models/brain/`, plus `config/consensus.yaml`,
`config/strategy_regime_filters.yaml`, `config/strategy_tiers.yaml`,
`scripts/run_hybrid.py`, `scripts/train_brain_daily.py`, and
`docs/*.md` additions + `tests/test_beta_*.py`,
`tests/test_consensus_*.py`, `tests/test_training_*.py`,
`tests/test_strategies_py_*.py`.

**MODIFIED (2 files only):**
- `core/main_brain_v2.py` — +~10 lines at end of `run()`
- `dashboard/state.py` — Decision dataclass +4 optional fields

Nothing else in QSC is modified.

---

## 8. Delivery Plan & Progress

| D | Scope | Status | Commit | Tests |
|---|-------|--------|--------|-------|
| D0 | Continuity layer (docs) | ✅ | pending | 427 |
| D1 | Skeleton + docs + config + trainer stub | ✅ | f796fd9 | 259 |
| D2 | Beta Brain 6 modules + 62 tests | ✅ | a07dcae | 325 |
| D3 | Training package + 35 tests | ✅ | 0cdd885 | 360 |
| D3c | Timezone auto-detect | ✅ | 103370d | 360 |
| D3d | Encoding-tolerant reader | ✅ | ea4e822 | 360 |
| D4a | Beta Signal + debate engine | ✅ | f6f1476 | 392 |
| D4b | Beta jury + verdict engine | ✅ | e9247be | 427 |
| D5a-1 | strategies_py infrastructure | ⏳ next | — | ~450 |
| D5a-2 | order_flow strategies | ⏳ | — | ~458 |
| D5a-3 | liquidity + supply_demand | ⏳ | — | ~468 |
| D5a-4 | rest + knowledge base | ⏳ | — | ~487 |
| D5b | BetaBrain + Arbiter + run_hybrid + main_brain patch | ⏳ CHECKPOINT | — | ~512 |

Checkpoint cadence: every 5th delivery (D5, D10, D15...).

---

## 9. Success Criteria

- [ ] QSC's 259 existing tests still pass.
- [ ] Beta Brain's tests pass.
- [ ] Hybrid runs end-to-end via `scripts/run_hybrid.py --once`.
- [ ] JSONL grows, rotates, archives.
- [ ] Trainer produces versioned state under `data/models/brain/`.
- [ ] Rollback switches `current.json` and brain reloads.
- [ ] 48h paper run with no unhandled exceptions.
- [ ] Dashboard shows consensus panel + Beta view.

---

## 10. References

- `docs/RESUME_PROMPT.md` — paste-into-new-chat resume file
- `docs/CONTEXT.md` — locked decisions + conventions
- `docs/PHASE_LOG.md` — phase narrative
- `docs/BETA_BRAIN.md` — Beta delivery log
- `docs/STEP_LOG.md` — full chronological step history
- `docs/FILE_TREE.md` — auto-generated file tree
- `PROJECT_STATE.md` — current snapshot
- `config/consensus.yaml` — Arbiter runtime config
