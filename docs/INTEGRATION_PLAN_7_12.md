# Integration Plan - Deliveries 7-12

Derived from the two book summaries (docs/RESOURCES_BOOKS_2.md).

Six new deliveries, each self-contained, tested, non-breaking.

---

## Delivery 7 - Multi-timeframe structure + HTF bias

**Why first:** Every subsequent strategy depends on knowing the HTF bias.

**Files:**
- core/htf_bias.py (compute HTF trend from W1/D1/H4 swing structure)
- strategies_py/ict_smc/bos_choch.py (BOS/CHoCH detection)
- Modify beta_brain/beta_brain.py (compute HTF bias, pass to registry)
- tests/test_htf_bias.py, tests/test_bos_choch.py (~15 tests)

**Deliverable:**
- HTF bias is available to every strategy as context
- BOS/CHoCH is a first-class strategy

---

## Delivery 8 - Liquidity primitives (EQH/EQL, SHC, Squeeze)

**Files:**
- strategies_py/liquidity/equal_highs_lows.py
- strategies_py/liquidity/stop_hunt_candle.py
- strategies_py/liquidity/squeeze.py
- tests/test_liquidity_primitives.py (~18 tests)

**Deliverable:**
- EQH/EQL zones detected and tracked
- SHC detection (with follow-through)
- Squeeze detection (top/bottom)

---

## Delivery 9 - SMC entry model (OBIM)

**Files:**
- strategies_py/ict_smc/obim.py (Order Block + Imbalance)
- strategies_py/ict_smc/ftm_entry.py (master FTM strategy)
- tests/test_smc_entries.py (~12 tests)

**Deliverable:**
- OBIM detection
- Full FTM entry: HTF bias + OBIM + SHC + LTF BOS -> BUY/SELL

---

## Delivery 10 - Market Profile (TPO) + POC shift

**Files:**
- core/market_profile.py (TPO calc, single prints, VA by time)
- strategies_py/order_flow/poc_shift.py
- strategies_py/order_flow/single_print_tail.py
- tests/test_market_profile.py (~14 tests)

**Deliverable:**
- Market Profile TPO calculations
- POC shift detection
- Single-print / tail detection

---

## Delivery 11 - Hybrid arbiter upgrade

**Files:**
- Modify consensus/arbiter.py (accept pattern_strength)
- Modify config/consensus.yaml (add size_boosters)
- Modify beta_brain/jury/verdict_engine.py (pass pattern metadata)
- tests/test_arbiter_boosters.py (~10 tests)

**Deliverable:**
- BOTH_AGREE + high-conviction pattern -> size boost (e.g., 1.25x)
- DISAGREE but Beta has "false breakout fade" -> possible override

---

## Delivery 12 - Adaptive SL from pattern

**Files:**
- Modify beta_brain/jury/risk_jury.py (accept optional sl_hint)
- Extract sl_hint from SHC wick, OB zone edge in relevant strategies
- tests/test_adaptive_sl.py (~8 tests)

**Deliverable:**
- Stop loss can be placed at pattern-derived level
- ATR remains fallback

---

## Execution Order and Rationale

1. Delivery 7 (HTF bias) - foundational
2. Delivery 8 (liquidity primitives) - enables 9
3. Delivery 9 (SMC entries) - highest-conviction setups
4. Delivery 10 (market profile) - completes Book 1 coverage
5. Delivery 11 (arbiter upgrade) - uses 7-10 signals for consensus
6. Delivery 12 (adaptive SL) - risk refinement on top of 7-11

After each delivery, run the backtest and compare PnL/Sharpe to the
previous baseline. Do not proceed if a delivery regresses the Sharpe.

---

## Backtest Protocol

Baseline: Delivery 6 backtest result on 10000 BTCUSDT 5m candles:
- Net PnL +5.68%
- PF 1.493
- Trades 28
- Real Sharpe ~0.5

Each new delivery's backtest must be run for comparison.
Track the following in docs/BACKTEST_ANALYSIS.md (append per delivery):
- Net PnL%, PF, total trades, Sharpe, max DD, per-strategy table

Accept a delivery only if the composite metric improves or is unchanged.
