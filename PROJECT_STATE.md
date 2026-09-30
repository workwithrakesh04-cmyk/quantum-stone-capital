# PROJECT STATE - Quantum Stone Capital

**Last updated:** 2026-10-01 01:24
**Repo:** https://github.com/workwithrakesh04-cmyk/quantum-stone-capital
**Local:** E:\quantum-stone-capital
**Branch:** main

## Current Snapshot
- **Last commit:** e9247be Hybrid Delivery 4b: Beta jury (risk + portfolio + final + verdict engine)
- **Tests passing:** 427 (pre-D0; will grow with 5a series)
- **Last checkpoint:** Phase 13 complete (hybrid era uses manual commits)
- **Last delivery:** D4b (Beta jury + verdict engine)
- **Next delivery:** 5a-1 (strategies_py infrastructure)

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
    git ls-files

## Running the Hybrid (once 5b lands)
    python scripts/run_hybrid.py --once    # one pass
    python scripts/run_hybrid.py           # continuous

## Training Cycle
    python scripts/train_brain_daily.py                 # train on newest JSONL
    python scripts/train_brain_daily.py --status        # show current + available
    python scripts/train_brain_daily.py --list          # list state folders
    python scripts/train_brain_daily.py --rollback DATE # rollback

