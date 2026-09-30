# PROJECT STATE - Quantum Stone Capital

**Last updated:** 2026-10-01 01:27
**Repo:** https://github.com/workwithrakesh04-cmyk/quantum-stone-capital
**Local:** E:\quantum-stone-capital
**Branch:** main

## Current Snapshot
- **Last commit:** 7b2a299 Delivery 0: continuity layer (docs + project state refresh)
- **Tests passing:** ~450 (D5a-1 landed; adding tests in later 5a series)
- **Last delivery:** D5a-1 (strategies_py infrastructure)
- **Next delivery:** 5a-2 (order_flow strategies)

## Quick Resume
- **docs/RESUME_PROMPT.md**  <- paste into a new chat to resume
- docs/CONTEXT.md            <- locked decisions + conventions
- docs/HYBRID_ARCHITECTURE.md <- system design
- docs/BETA_BRAIN.md         <- Beta Brain delivery log
- docs/PHASE_LOG.md          <- phase narrative
- docs/STEP_LOG.md           <- full step history
- docs/FILE_TREE.md          <- auto-generated tree

## Resume Commands
    cd E:\quantum-stone-capital
    .\venv\Scripts\Activate.ps1
    pytest tests/ -q
    git log --oneline -10

## Running the Hybrid (once 5b lands)
    python scripts/run_hybrid.py --once

## Training Cycle
    python scripts/train_brain_daily.py
    python scripts/train_brain_daily.py --status
    python scripts/train_brain_daily.py --list
    python scripts/train_brain_daily.py --rollback DATE

