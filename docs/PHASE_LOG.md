# PHASE LOG - Quantum Stone Capital

High-level narrative per phase. Detail per step is in
`docs/STEP_LOG.md`. This file captures the *what* and *why* at a
scope larger than individual steps.

---

## Phase 1 — Repository + Core Architecture
**2026-09-27**
Created folder structure, config, core pricing/risk/main_brain,
microstructure Kyle λ. First commit + GitHub push.

## Phase 2 — Data Layer + Logging + Time Utils
**2026-09-27**
Loguru structured logging, time sessions/killzones, math utils
(z-score, ATR, Sharpe, MDD), synthetic BTCUSD 5m CSV for tests.

## Phase 3 — Microstructure + Strategies + Signal Filter
**2026-09-27**
Kyle λ + Bayesian FV + spread estimator integrated into
`microstructure/engine.py`. Strategy registry with YAML auto-
discovery and regime matching. Extreme-only z-score filter.

## Phase 4 — Execution Engine + Order + ICT/SMC Strategies
**2026-09-27**
Slippage + TWAP splitting + fill simulation. Order dataclass.
ICT/SMC strategy YAML library (Fede, Woods, CRT, Deivid traps).

## Phase 5 — Elliott Wave + Harmonic + Fibonacci
**2026-09-27**
Fibonacci retracements/extensions, 5-wave Elliott validation,
Gartley/Butterfly/Cypher/Shark/AB=CD patterns, strategy YAMLs.

## Phase 6 — ML Pipeline
**2026-09-27**
Alpha factors, technical indicators, 15-feature vector,
XGBoost/LightGBM boosted models, PPO fallback wrapper,
walk-forward with purging/embargoing, metrics (Sharpe, IC,
deflated Sharpe).

## Phase 7 — Order Flow + Footprint + VPA
**2026-09-27**
Delta/cumulative delta/absorption, footprint levels/POC,
Coulling VPA (effort vs result), layer6 wrapper, strategy YAMLs.

## Phase 8 — Workers + Jurors + Debate
**2026-09-27**
Bull/Bear/Hold workers, 3 jurors (risk/strategy/execution),
debate engine orchestration. 196 tests.

## Phase 9 — Pipeline Orchestration + Brokers + Live
**2026-09-27**
MarketContext, PipelineResult, strategy_selector, trade_proposal,
main_brain_v2. Paper + MT5 + Sim brokers. live_runner.

## Phase 10 — Live Feeds + Multi-Account Broker Pool
**2026-09-27**
Binance/Biquote/Yahoo/Gud feeds. Aggregator. config/accounts.yaml
for personal + prop. sim_broker multi-account.

## Phase 11 — Test Hardening
**2026-09-27**
Fixed 3 test bugs, all feeds working, tests green.

## Phase 12 — Dashboard
**2026-09-28**
FastAPI + WebSocket + Chart.js. TraderLadder + journal hybrid UI.
Equity curve, calendar heatmap, metric cards.

## Phase 13 — Prop Rules + Account Routing
**2026-09-28**
Prop firm rule engine (`core/prop_rules.py`), account router with
personal/prop fallback, trade router, dashboard routing panel.
285 total tests (per PROJECT_STATE) — actual current baseline: 259.

---

## Hybrid Era — HFT_Brain Merge

**Design approved 2026-10-01.**
See `docs/HYBRID_ARCHITECTURE.md` and `docs/CONTEXT.md` for the full
design and locked decisions.

**Deliveries completed:**
- D0 (this file + RESUME_PROMPT + CONTEXT + doc refreshes) — 2026-10-01
- D1 skeleton + docs + config + trainer stub — f796fd9
- D2 Beta Brain 6 modules + 62 tests — a07dcae
- D3 training package + 35 tests — 0cdd885
- D3c timezone auto-detect — 103370d
- D3d encoding-tolerant reader — ea4e822
- D4a Beta Signal + debate — f6f1476
- D4b Beta jury — e9247be
- D5a-1 strategies_py infra — pending
- D5a-2 order_flow — pending
- D5a-3 liquidity + supply_demand — pending
- D5a-4 rest + knowledge — pending
- D5b integration + CHECKPOINT — pending

**Total tests at Phase 13 close:** 259
**Total tests now:** 427 (pre-D0), ~450 after D5a-1
