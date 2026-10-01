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
---

## Delivery 5a-4a — 2026-10-01 — Final 19 Strategies
Commit: pending

**Created:**
- `strategies_py/ict_smc/fvg_strategy.py`, `luxalgo_fvg.py` (2)
- `strategies_py/patterns/diamond_cancan.py`, `head_shoulders.py`,
  `double_top_bottom.py`, `engulfing_pinbar.py`, `reversal_123.py` (5)
- `strategies_py/ml_adaptive/adaptive_rsi_ml.py`, `ai_source_ma.py`,
  `ai_trend_flow.py`, `ml_momentum.py`, `ml_rsi.py` (5)
- `strategies_py/volatility/mad_loop_bb.py`, `mad_loop_fl.py`,
  `mad_loop_combined.py`, `apex_flow.py`, `rmd_trail.py` (5)
- `strategies_py/trend/ichimoku_rsi.py`, `cardwell_rsi.py`,
  `intermarket.py` (3)
- `tests/test_strategies_py_final_batch.py` (20 tests)

**Tests:** 469 → ~489 (+20)

**Notes:**
- ML strategies (adaptive_rsi_ml, ai_source_ma, ai_trend_flow,
  ml_momentum) use simplified logic in 5a-4a. Full k-NN analog
  behavior can be added in a future delivery once we see live results.
- `ml_rsi` uses level-based logic (oversold <25, overbought >75)
- Loader's module list now fully populated; `load_all_strategies()`
  should now return 42 classes

**Next:** 5a-4b (knowledge base: knowledge_loader + 10 book JSONs +
integration into strategies_py.base._get_rule_weight)
---

## Delivery 5a-4b — 2026-10-01 — Knowledge Base Port
Commit: pending

**Created:**
- `knowledge/books_index.json`
- `knowledge/book_52_master_the_markets.json` (VSA)
- `knowledge/book_56_phantom_notebook.json` (Order blocks, FVG)
- `knowledge/book_60_rcv_notes.json` (Liquidity sweeps)
- `knowledge/book_61_supply_demand_1.json` (DBR/RBR/DBD/RBD)
- `knowledge/book_62_supply_demand_2.json` (Quasimodo, CanCan, 3Drive)
- `knowledge/book_trader_dale_orderflow.json` (Volume clusters)
- `knowledge/book_trading_orderflow.json` (Trapped traders, COT)
- `knowledge/book_volume_profile_nextgen.json` (POC, VAH/VAL)

**Rewrote:**
- `knowledge/knowledge_loader.py` (full query API)

**Modified:**
- `strategies_py/base.py` — `_get_rule_weight()` now queries knowledge base
  (option A: silent fallback to 0.5 if unavailable)

**Created tests:**
- `tests/test_knowledge_loader.py` (8 tests)

**Tests:** 489 → ~497 (+8)

**Strategy audit:** 38 strategies load correctly. HFT_Brain has 42
files in strategies/ of which 4 are infrastructure (`__init__.py`,
`base_strategy.py`, `strategy_registry.py`, `tier_manager.py`). Parity
achieved: 42 - 4 = 38.

**Next:** 5b (BetaBrain wrapper + ConsensusArbiter + run_hybrid.py
+ main_brain_v2 patch + dashboard patch) — CHECKPOINT
---

## Delivery 5b - 2026-10-01 - Full Hybrid Integration (CHECKPOINT)
Commit: pending

**Created (Part A):**
- config/beta_personal.yaml
- config/beta_prop.yaml
- beta_brain/beta_brain.py
- consensus/agreement.py
- consensus/arbiter.py
- consensus/__init__.py
- scripts/run_hybrid.py

**Modified (Part B) - only 2 QSC files touched in entire hybrid:**
- core/main_brain_v2.py   (+10 lines: optional Beta+Arbiter hook)
- dashboard/state.py      (Decision +6 optional fields)

**Created (Part C):**
- tests/test_beta_brain.py (8 tests)
- tests/test_consensus_arbiter.py (12 tests)
- tests/test_hybrid_integration.py (8 tests)

**Tests:** 497 -> 525 (+28)

**How run_hybrid.py works (dry run):**
1. Calls QSC Brain via MainBrainV2.run
2. Calls BetaBrain.run (silent on failure)
3. Calls ConsensusArbiter.decide
4. Writes hybrid Decision to dashboard state
5. Writes JSONL to logs/consensus/YYYY-MM-DD.jsonl
6. Does NOT execute trades

**Execution:** remains in scripts/run_brain.py.

**Safety:**
- main_brain_v2 patch auto-reverted if import fails
- BetaBrain failure never breaks QSC (silent + warning)
- Arbiter never raises even with None inputs

**Hybrid era COMPLETE.** All 5 deliveries shipped.
---

## Delivery 6 - 2026-10-01 - BTC Backtest Runner
Commit: pending

**Created:**
- backtest/__init__.py
- backtest/beta_backtester.py  (core engine)
- backtest/reporter.py         (terminal + file reports)
- scripts/backtest_beta.py     (CLI)
- tests/test_beta_backtester.py (12 tests)

**Modified:** none

**Tests:** 525 -> ~537

**Purpose:** Simulate Beta Brain over historical BTC 5m candles.
Answers: do the 38 strategies + debate + jury produce profit on real history?

**How it works:**
1. HistoricalLoader fetches N candles for symbol (BTCUSDT).
2. Loop over candles from warmup: regime tag -> strategies -> debate
   -> jury -> paper trade. Process open trades against each new candle.
3. Close remaining at end. Compute Sharpe/Sortino/Calmar, per-strategy,
   per-regime, and per-direction aggregations.

**Output:**
- Terminal report (headline metrics + 3 tables)
- data/logs/backtest_beta_<symbol>_<ts>.txt
- data/logs/backtest_beta_<symbol>_<ts>.json
- data/logs/backtest_beta_<symbol>_<ts>_trades.csv

**CLI:**
python scripts/backtest_beta.py --symbol BTCUSDT --candles 10000 --warmup 100

**Next:** analyze results; use per-strategy + per-regime tables to
decide which strategies to shadow/demote, and whether to move to
shadow trading (Delivery 7).

---

## Delivery 6c - 2026-10-01 - Honest Metrics + Timeout Enforcement
Commit: pending

**Modified:**
- `beta_brain/performance_metrics.py` - Sharpe `periods_per_year` now optional,
  auto-inferred from trade count + period; Sortino downside deviation
  computed over all trades relative to MAR (was std-of-losers)
- `backtest/beta_backtester.py` - `_derive_max_hold_bars()` reads config;
  stage-by-stage rejection counters; `enrich()` receives `period_days`
- `config/beta_personal.yaml` - `enable_timeout_exits: true`
- `config/beta_prop.yaml`     - `enable_timeout_exits: true`

**Created:**
- `tests/test_d6c_performance_metrics.py` (26 tests)
- `tests/test_d6c_backtester_config.py` (13 tests)
- `docs/D6C_REPORT.md`

**Untouched:**
- `beta_brain/paper_trader.py` (timeout branch already existed)

**Tests:** 561 -> 588 (final).

**Bugs closed (from D6 analysis):**
1. Sharpe annualization inflated (16.95 -> 1.08 real)
2. `max_hold_bars` not enforced (0 -> 12, 11 TMO exits fire)
3. Rejection diagnostic single-counter (now 4-stage funnel)
4. (bonus) Sortino formula (0.08 -> 1.65 real)

**Key finding:** enabling the 60-min timeout reduced net PnL by
$387 but improved risk-adjusted metrics (max DD 6.62% -> 5.35%).
The higher pre-D6c PnL was partly from holding losers indefinitely.

**Correction:** the D7 shadow recommendation in BACKTEST_ANALYSIS.md
(mad_bb, rmd_trail, adaptive_rsi_ml) is invalidated by the D6c run -
those are now the top 3 PnL contributors. Real shadow candidates
are flag_limits and rbd_dbr.

**Next:** D7 - tune min-confidence gate + VOLATILE block + TMO analysis.

---

## Delivery 7c - 2026-10-01 - Shadow TMO Losers + Diagnostic Aggregations
Commit: pending

**Modified:**
- `config/strategy_regime_filters.yaml` - added `rbd_dbr` + `flag_limits`
  to `global_disable`
- `config/strategy_tiers.yaml` - moved `rbd_dbr` to tier_4_shadow,
  added `flag_limits` to tier_4_shadow, added "documentation only" note
- `backtest/beta_backtester.py` - added 3 diagnostic aggregations:
  `confidence_histogram`, `volatile_by_strategy`, `tmo_by_strategy`;
  raw per-debate records kept in `self._debate_records`
- `tests/test_d6c_backtester_config.py` - fixed 2 broken tests from
  D7c get_diagnostics change (added missing fixtures + import)

**Created:**
- `tests/test_d7_diagnostics.py` (15 tests)
- `docs/D7_REPORT.md`

**Tests:** 588 (D6c) -> 603 (D7c). Net +15.

**Key findings:**
1. Shadowing `rbd_dbr` + `flag_limits` caused a cascade: fewer signals
   -> HOLD wins more -> 58 -> 31 trades. All remaining strategies
   have WR >= 57%.
2. The 0.70 confidence gate is correct: histogram shows clean
   separation (0.6-0.7 bucket: 19/20 rejected; 0.7-0.8 bucket:
   28/28 passed). D6c Focus 1 is resolved - do not lower the gate.
3. VOLATILE flipped -$431.60 -> +$43.43. Per-strategy attribution
   shows the loss came from `adaptive_rsi_ml` + `mad_bb` in
   VOLATILE only; both are profitable overall.
4. TMO exits dropped 11 -> 4, all winners. D6c Focus 3 resolved.

**Small-sample caveat:** Sharpe 4.84 / Sortino 9.10 / Calmar 9.92
are on 31 trades. Do not cite as stable. D7b must validate on a
larger window.

**Architecture note:** `strategy_tiers.yaml` is currently
documentation only - the registry reads `global_disable` in
`strategy_regime_filters.yaml`. Moving a strategy to tier_4_shadow
does not shadow it. A future delivery must wire `TierManager` into
`StrategyRegistry`.

**Next:** D7b - rerun on larger window (20k candles or walk-forward).
Pure measurement. No config change.

---

## Delivery 7b - 2026-10-01 - 20k-Candle Validation
Commit: pending

**Modified:** none (source or config)
**Created:** `docs/D7B_REPORT.md`

**Tests:** 603 (unchanged - no code touched)

**Purpose:** Validate D7c's config changes on 2x the data.

**Result: D7c's magnitude INVALIDATED.**

| Metric | D6c (10k) | D7c (10k) | D7b (20k) |
|---|---|---|---|
| Sharpe | 1.08 | 4.84 | **0.17** |
| Net PnL % | +12.34% | +14.58% | **+2.76%** |
| Max DD % | 5.35% | 1.47% | **6.56%** |
| Trades | 58 | 31 | 54 |

D7c's Sharpe 4.84 was a small-sample artifact. On 20k it reverts
to 0.17. The D7c config change (shadowing `rbd_dbr` + `flag_limits`)
is not validated as a risk-adjusted improvement.

**What D7b confirmed:**
- 0.70 confidence gate is correct (clean separation on 20k)
- 60-min TMO is correct (12 exits, all strategy sums positive)
- `adaptive_rsi_ml` is a consistent VOLATILE loser (0% WR across
  both samples; -$502.76 combined)
- `mad_bb` is NOT a VOLATILE loser (flipped positive on 20k)

**New finding:** CHOPPY regime is a net loser (21 trades, 19% WR,
-$146.24). D6c had only 4 CHOPPY trades so this was invisible.

**Bottom line:** the strategy set produces +2.76% over 70 days
with Sharpe 0.17. This is a flat system on a risk-adjusted basis.

**Recommendation for next:** D8b walk-forward validation. D7b
proved single-window backtests mislead. Walk-forward (10 windows)
is the correct next step.