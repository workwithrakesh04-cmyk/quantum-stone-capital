# Hybrid Architecture - Quantum Stone Capital + HFT_Brain

Status: Design approved. Delivery 1 of 5.
Created: 2026-10-01
Owner: Quantum Stone Capital

## 1. Naming Convention

- QSC Brain  = Quantum Stone Capital's MainBrainV2 (core/main_brain_v2.py)
- Beta Brain = HFT_Brain's ported pipeline (beta_brain/beta_brain.py)
- Arbiter    = ConsensusArbiter (consensus/arbiter.py)
- Trainer    = Daily training loop (training/trainer.py)

## 2. Non-Negotiable Constraints

1. QSC's existing pipeline is NOT rewritten. Only ~10 lines added to
   core/main_brain_v2.py in Delivery 5.
2. No folder is replaced. New work lives in beta_brain/, strategies_py/,
   knowledge/, consensus/, backtest/, training/.
3. Beta Brain is toggleable via config/consensus.yaml.
4. Every arbitration is logged to logs/consensus/YYYY-MM-DD.jsonl.

## 3. Layout After Full Integration

    quantum-stone-capital/
    |-- core/           QSC Brain (existing, untouched)
    |-- brokers/        QSC (existing)
    |-- feeds/          QSC (existing)
    |-- microstructure/ QSC (existing)
    |-- strategies/     QSC YAML library (existing)
    |-- ml/             QSC ML stack (existing)
    |-- dashboard/      QSC dashboard (existing)
    |-- config/         QSC + consensus.yaml
    |-- beta_brain/     NEW - HFT_Brain pipeline
    |-- strategies_py/  NEW - 42 Python strategies
    |-- knowledge/      NEW - 62-book knowledge base
    |-- consensus/      NEW - Arbiter layer
    |-- backtest/       NEW - Beta backtest runners
    |-- training/       NEW - Daily trainer
    |-- logs/consensus/ JSONL + archive/
    +-- data/models/brain/  versioned trained state

## 4. Beta Brain Pipeline

    MarketContext -> regime_tagger.tag() -> strategies_py.registry.run_all()
    -> debate.engine.run() -> jury.verdict_engine.run() -> BetaVerdict

Beta Brain runs 5m only.

## 5. Arbiter Decision Matrix

    QSC Brain | Beta Brain | Consensus  | Size
    ----------|------------|------------|-----
    LONG      | BUY        | BOTH_AGREE | 1.0x
    SHORT     | SELL       | BOTH_AGREE | 1.0x
    LONG      | HOLD       | QSC_ONLY   | 0.5x
    SHORT     | HOLD       | QSC_ONLY   | 0.5x
    HOLD      | BUY        | BETA_ONLY  | 0.5x
    HOLD      | SELL       | BETA_ONLY  | 0.5x
    LONG      | SELL       | DISAGREE   | 0.0x
    SHORT     | BUY        | DISAGREE   | 0.0x
    HOLD      | HOLD       | BOTH_HOLD  | 0.0x

## 6. Daily Training Lifecycle

Live hours: QSC + Beta + Arbiter append to logs/consensus/YYYY-MM-DD.jsonl
Trainer run:  read JSONL, compute new weights + thresholds,
              write data/models/brain/YYYY-MM-DD/,
              update current.json, archive JSONL.

Targets (Q16=B): Beta strategy weight multipliers + Arbiter thresholds.
Rollback (Q19=C): archive-only, manual via --rollback YYYY-MM-DD.

## 7. Files Touched During Full Build

NEW (unlimited): beta_brain/*, strategies_py/*, knowledge/*, consensus/*,
backtest/*, training/*, logs/consensus/*, data/models/brain/*,
config/consensus.yaml, scripts/run_hybrid.py, scripts/train_brain_daily.py,
docs/HYBRID_ARCHITECTURE.md, docs/BETA_BRAIN.md, tests/test_beta_*.py,
tests/test_consensus_*.py, tests/test_training_*.py

MODIFIED (2 files only):
- core/main_brain_v2.py  ->  ~10 lines added at end of run()
- dashboard/state.py     ->  Decision dataclass gets 4 optional fields

## 8. Delivery Plan

D1: skeleton + docs + config + trainer stub  [THIS DELIVERY]
D2: beta_brain/ 6 standalone modules + tests
D3: training/ full logic + tests
D4: beta_brain/debate/ + jury/ ports + tests
D5: strategies_py/ + BetaBrain + Arbiter + main_brain_v2 patch + run_hybrid

Checkpoint every 5 deliveries.

## 9. Success Criteria

- QSC's 285 existing tests still pass.
- Beta Brain's tests pass.
- Hybrid runs end-to-end via scripts/run_hybrid.py --once.
- JSONL grows, rotates, archives.
- Trainer produces versioned state under data/models/brain/.
- Rollback switches current.json and brain reloads.
