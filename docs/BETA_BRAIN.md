# Beta Brain - Work Log

Detailed log of Beta Brain's evolution. Updated after every delivery
that touches `beta_brain/`, `strategies_py/`, `consensus/`, or
`training/`.

---

## Delivery 1 — 2026-10-01 — Skeleton
Commit: `f796fd9`

**Created:**
- `beta_brain/`, `beta_brain/debate/`, `beta_brain/jury/`
- `strategies_py/`, `knowledge/`, `consensus/`, `backtest/`,
  `training/`
- `logs/consensus/archive/`, `data/models/brain/`
- `config/consensus.yaml`
- `scripts/train_brain_daily.py` (stub)
- `docs/HYBRID_ARCHITECTURE.md`, `docs/BETA_BRAIN.md`

**Modified:** none
**Tests:** none yet (skeleton only)

---

## Delivery 2 — 2026-10-01 — 6 Standalone Modules
Commit: `a07dcae`

**Created:**
- `beta_brain/regime_tagger.py` — 5-regime classifier (BTC 5m)
- `beta_brain/account_guard.py` — daily reset + kill switch + loss scaling
- `beta_brain/paper_trader.py` — SL-before-TP intrabar sim
- `beta_brain/performance_metrics.py` — Sharpe/Sortino/Calmar/expectancy
- `beta_brain/strategy_analyzer.py` — per-strategy PnL attribution
- `beta_brain/shadow_tracker.py` — hypothetical trades for disabled strategies
- 6 test files (~62 tests)

**Modified:** none
**Tests:** 259 → 325 (+66)

**Fixes during delivery:**
- ShadowTracker test used flat candles (ATR=0) causing 8 failures.
  Fixed by generating OHLC with real high/low ranges.

---

## Delivery 3 — 2026-10-01 — Training Package
Commit: `0cdd885`

**Created:**
- `consensus/audit.py` — JSONL writer + rotation + archive
- `training/loader.py` — TrainingSample + TrainingLoader
- `training/strategy_weights.py` — win-rate-driven weight adjuster
- `training/arbiter_thresholds.py` — per-regime beta-disable logic
- `training/trainer.py` — orchestrates the daily cycle
- `training/rollback.py` — manual pointer switch
- `scripts/train_brain_daily.py` — full CLI (replaces stub)
- 4 test files (~35 tests)

**Tests:** 325 → 360 (+35)

**Fixes during delivery (3b, 3c, 3d):**
- **3b:** UTF-8 BOM in `current.json` broke `json.load`. Fixed by
  reading with `utf-8-sig`.
- **3c:** Trainer defaulted to UTC day, but user wrote JSONL with
  local day. Fixed by auto-detecting newest active JSONL.
- **3d:** JSONL files written by PowerShell UTF-8 (with BOM) broke
  the reader. Fixed with encoding-tolerant reader
  (`utf-8`, `utf-8-sig`, `utf-16`, `utf-16-le`, `utf-16-be`,
  `latin-1` fallback chain).

---

## Delivery 4a — 2026-10-01 — Signal + Debate
Commit: `f6f1476`

**Created:**
- `beta_brain/signal.py` — self-contained Signal dataclass
- `beta_brain/debate/__init__.py`
- `beta_brain/debate/transcript.py` — Argument + DebateTranscript
- `beta_brain/debate/buy_bot.py`, `sell_bot.py`, `hold_bot.py`
- `beta_brain/debate/argument_scorer.py`
- `beta_brain/debate/engine.py` — 3-round orchestrator
- 4 test files (~32 tests)

**Tests:** 360 → 392 (+32)

**Fix during delivery:**
- `test_buy_bot_no_signals` expected 0.0 but got 0.037 (momentum
  bonus). Fixed test to use neutral context (momentum=0).

---

## Delivery 4b — 2026-10-01 — 3-Jury Verdict System
Commit: `e9247be`

**Created:**
- `beta_brain/jury/__init__.py`
- `beta_brain/jury/transcript.py` — RiskVerdict, PortfolioVerdict, JuryVerdict
- `beta_brain/jury/risk_jury.py` — ATR SL + loss-scaled sizing + notional cap
- `beta_brain/jury/portfolio_jury.py` — position count + exposure limits
- `beta_brain/jury/final_jury.py` — both-must-approve combiner
- `beta_brain/jury/verdict_engine.py` — orchestrator for the 3 juries
- 5 test files (~35 tests)

**Tests:** 392 → 427 (+35)

**Notes:**
- VerdictEngine takes `config` in constructor OR via `set_config()`.
  This lets one engine handle both personal and prop accounts with
  different configs.

---

## Delivery 0 — 2026-10-01 — Continuity Layer
Commit: pending

**Created:**
- `docs/RESUME_PROMPT.md`
- `docs/CONTEXT.md`
- `docs/PHASE_LOG.md`

**Rewrote:**
- `docs/BETA_BRAIN.md` (this file — expanded)
- `docs/HYBRID_ARCHITECTURE.md` (updated to current state)
- `PROJECT_STATE.md` (refreshed)

**Purpose:** Fill gaps that `checkpoint.ps1` and `PROJECT_STATE.md`
had been referencing for weeks without those files existing. Also
creates a single-file entry point for resuming in a new chat if the
current chat hits its context limit.

**Tests:** 427 (no code changes)

---

## Delivery 5a-1 — Pending
**Scope:** `strategies_py/base.py`, `registry.py`, `tier_manager.py`,
`loader.py`, `config/strategy_regime_filters.yaml`,
`config/strategy_tiers.yaml`, plus ~23 tests.

## Delivery 5a-2 — Pending
**Scope:** order_flow strategies (8 files + 8 tests)

## Delivery 5a-3 — Pending
**Scope:** liquidity + supply_demand (10 files + 10 tests)

## Delivery 5a-4 — Pending
**Scope:** ICT/SMC + patterns + ml_adaptive + volatility + trend +
`knowledge/` (~19 strategies + knowledge base + tests)

## Delivery 5b — Pending (CHECKPOINT)
**Scope:** `beta_brain/beta_brain.py`, `consensus/arbiter.py`,
`scripts/run_hybrid.py`, patch `core/main_brain_v2.py`,
patch `dashboard/state.py`. ~25 tests.
Then run `.\scripts\checkpoint.ps1 -Label "Hybrid deliveries 1-5 complete"`.

---

## Support Modules Summary (state after D4b)

| Module | Purpose |
|--------|---------|
| `signal.py` | Beta Signal dataclass |
| `regime_tagger.py` | 5-regime classifier (BTC 5m) |
| `account_guard.py` | Daily reset + kill switch + loss scaling |
| `paper_trader.py` | Sim execution with SL-before-TP |
| `performance_metrics.py` | Sharpe/Sortino/Calmar/expectancy |
| `strategy_analyzer.py` | Per-strategy PnL attribution |
| `shadow_tracker.py` | Hypothetical trades for disabled strategies |
| `debate/` | 3-round BUY/SELL/HOLD debate |
| `jury/` | 3-jury verdict (risk, portfolio, final) |

---

## Delivery 5a-1 — 2026-10-01 — strategies_py Infrastructure
Commit: pending

**Created:**
- `strategies_py/base.py` — BaseStrategy abstract + helpers
- `strategies_py/registry.py` — StrategyRegistry with regime filter + tier
- `strategies_py/tier_manager.py` — TierManager
- `strategies_py/loader.py` — auto-discovery loader
- 8 category packages (`order_flow/`, `liquidity/`, `supply_demand/`,
  `ict_smc/`, `patterns/`, `ml_adaptive/`, `volatility/`, `trend/`)
  with `__init__.py`
- `config/strategy_regime_filters.yaml` (from HFT_Brain)
- `config/strategy_tiers.yaml` (from HFT_Brain)
- 4 test files (~23 tests)

**Tests:** 427 → ~450 (+23)

**Notes:**
- Loader silently skips modules that don't exist yet (later deliveries
  add them)
- Registry's `_is_active()` applies: regime_enable_only, regime_rules
  block, trade_caps
- Tier manager understands per-account enabled/disabled tiers

**Next:** 5a-2 (order_flow strategies: absorption, delta_divergence,
stacked_imbalance, trapped_traders, naked_poc, poc_strategy,
value_area, volume_cluster)
---

## Delivery 5a-2 — 2026-10-01 — Order Flow Strategies
Commit: pending

**Created:**
- `strategies_py/order_flow/absorption.py`
- `strategies_py/order_flow/delta_divergence.py`
- `strategies_py/order_flow/stacked_imbalance.py`
- `strategies_py/order_flow/trapped_traders.py`
- `strategies_py/order_flow/naked_poc.py`
- `strategies_py/order_flow/poc_strategy.py`
- `strategies_py/order_flow/value_area.py`
- `strategies_py/order_flow/volume_cluster.py`
- `tests/test_strategies_py_order_flow.py` (9 tests)

**Tests:** 450 → ~458 (+8)

**Notes:**
- All 8 strategies instantiate, run on flat candles, and return valid Signals
- delta_divergence and stacked_imbalance require buy_volume/sell_volume fields
  (only populated on live TickBuffer data; return HOLD on historical candles)
- Loader in `strategies_py/loader.py` now finds these classes automatically

**Next:** 5a-3 (liquidity + supply_demand: liquidity_sweep,
false_breakout, bs_ss_liquidity, turtle_soup, quasimodo, rbd_dbr,
sd_zones, ftr_compression, flag_limits, three_drive)
---

## Delivery 5a-3 — 2026-10-01 — Liquidity + Supply/Demand
Commit: pending

**Created:**
- `strategies_py/liquidity/liquidity_sweep.py`
- `strategies_py/liquidity/false_breakout.py`
- `strategies_py/liquidity/bs_ss_liquidity.py`
- `strategies_py/liquidity/turtle_soup.py`
- `strategies_py/liquidity/quasimodo.py`
- `strategies_py/supply_demand/rbd_dbr.py`
- `strategies_py/supply_demand/sd_zones.py`
- `strategies_py/supply_demand/ftr_compression.py`
- `strategies_py/supply_demand/flag_limits.py`
- `strategies_py/supply_demand/three_drive.py`
- `tests/test_strategies_py_liquidity_sd.py` (10 tests)

**Tests:** 459 → ~469 (+10)

**Next:** 5a-4 (ICT/SMC + patterns + ML + volatility + trend, plus
knowledge base — the final 5a batch)