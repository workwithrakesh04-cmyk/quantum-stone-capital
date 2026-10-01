# PROJECT STATE - Quantum Stone Capital

**Last updated:** 2026-10-01 19:12
**Repo:** https://github.com/workwithrakesh04-cmyk/quantum-stone-capital
**Local:** E:\quantum-stone-capital
**Branch:** main

## Current Snapshot
- **Last commit (pre-checkpoint):** 13ed9b6 Fix: repair poc_strategy.py syntax
- **Tests passing:** ~537
- **Last delivery:** 6 (BTC backtest runner)
- **Next:** Run backtest, review per-strategy + per-regime tables

## Hybrid Status: COMPLETE + BACKTESTABLE
- QSC Brain: untouched (except +10-line hook)
- Beta Brain: 38 strategies + debate + 3-jury
- Arbiter: BOTH_AGREE / QSC_ONLY / BETA_ONLY / DISAGREE / BOTH_HOLD
- Trainer: daily JSONL -> weights (needs shadow trades for real data)
- Backtest: Beta-only historical simulation (this delivery)

## Quick Resume
- **docs/RESUME_PROMPT.md**  <- paste into a new chat
- docs/CONTEXT.md, docs/HYBRID_ARCHITECTURE.md, docs/BETA_BRAIN.md
- docs/PHASE_LOG.md, docs/STEP_LOG.md, docs/FILE_TREE.md

## Run
    python scripts/run_brain.py --once     # QSC alone (executes)
    python scripts/run_hybrid.py --once    # Hybrid (dry run)
    python scripts/train_brain_daily.py    # Daily training
    python scripts/backtest_beta.py        # Backtest Beta Brain

