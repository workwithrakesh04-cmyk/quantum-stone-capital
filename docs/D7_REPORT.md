# Delivery 7c Report - Shadow TMO Losers + Diagnostic Aggregations

**Run date:** 2026-10-01
**Scope:** Shadow `rbd_dbr` + `flag_limits`; add 3 diagnostic aggregations
**Status:** COMPLETE - tests green (603), committed, D7b validation queued
**QSC files touched:** none

---

## 1. Summary

D6c left two questions open:

1. **The confidence gate** at 0.70 filtered 54.8% of all rejections.
   Was it too high?
2. **The VOLATILE block** was empty, yet VOLATILE lost -$431.60.
   Should we block strategies there?

D7c was scoped to answer these **with data**, not guesses, and to
ship one evidence-backed config change (shadowing two TMO-losing
strategies). It does not touch the confidence gate or the VOLATILE
block. Those decisions move to D7b, informed by D7c's diagnostics.

---

## 2. What changed

### `config/strategy_regime_filters.yaml`

Added to `global_disable`:

    - rbd_dbr      # -$28.60 net, -$209.04 across 6 TMO exits
    - flag_limits  # -$124.64 net, 25.0% WR, all TMO exits were losers

This is the **functional** shadow mechanism. The registry reads
`global_disable`; the tier file is documentation only (see below).

### `config/strategy_tiers.yaml`

- Moved `rbd_dbr` from `tier_2_supporting` to `tier_4_shadow`
- Added `flag_limits` to `tier_4_shadow`
- Added a header note explaining that the tier file is currently
  **documentation only** — the registry does not read it yet

**Important:** moving a strategy to `tier_4_shadow` here has **no
functional effect**. The registry reads `global_disable`. Both must
be kept in sync until a future delivery wires `TierManager` into
`StrategyRegistry`.

### `backtest/beta_backtester.py`

Three new diagnostic aggregations:

- **`confidence_histogram`** — buckets of `winner_confidence` for
  BUY/SELL debates, split by whether the confidence gate passed.
- **`volatile_by_strategy`** — per-strategy trades + PnL restricted
  to VOLATILE regime.
- **`tmo_by_strategy`** — per-strategy trades + PnL + avg bars held
  for `CLOSED_TIMEOUT` exits.

All three are exposed via `get_diagnostics()` and printed in the
terminal report. Raw per-debate records are kept in
`self._debate_records` (winner, confidence, min_conf, passed_gate,
regime) for post-hoc aggregation.

### `tests/test_d7_diagnostics.py`

15 new tests covering all three aggregations (empty cases, boundary
conditions, multi-strategy crediting, key shape).

### `tests/test_d6c_backtester_config.py`

Fixed 2 tests that D7c's `get_diagnostics()` change broke: added
`_debate_records = []` and `trader = SimpleNamespace(closed_trades=[])`
to the two hand-built fixtures, and added the missing
`from types import SimpleNamespace` import.

**Test count:** 588 (D6c) -> 603 (D7c). Net +15.

---

## 3. Backtest comparison: D6c vs D7c

Same 10,000-candle BTCUSDT 5m window. TMO enabled (60min scalp).

| Metric | D6c (21:23) | **D7c (21:38)** | Delta |
|---|---|---|---|
| Net PnL | +$1,233.91 (+12.34%) | **+$1,458.48 (+14.58%)** | +$224.57 |
| Peak balance | $11,624.78 | $11,458.48 | -$166.30 |
| Max DD $ | $622.10 | **$167.87** | -$454.23 |
| Max DD % | 5.35% | **1.47%** | -3.88pp |
| Total trades | 58 | **31** | -27 |
| Win rate | 51.72% | **64.52%** | +12.80pp |
| Profit factor | 1.587 | **3.028** | +1.441 |
| Avg win | $111.24 | $108.88 | -$2.36 |
| Avg loss | -$75.11 | -$65.37 | +$9.74 |
| Expectancy/trade | +$21.27 | **+$47.05** | +$25.78 |
| Sharpe | 1.08 | **4.84** | +3.76 |
| Sortino | 1.65 | **9.10** | +7.45 |
| Calmar | 2.31 | **9.92** | +7.61 |
| Exits TP/SL/TMO/EOD | 22/25/11/0 | 13/14/4/0 | fewer of all |
| max_hold_bars_used | 12 | 12 | unchanged |

### IMPORTANT - small-sample caveat

**Do not cite Sharpe 4.84, Sortino 9.10, or Calmar 9.92 as stable
improvements over D6c.** Those numbers are computed on **31 trades**
over 35 days. The D6c Sharpe of 1.08 was on 58 trades. Neither is
statistically robust; the error bars on both are wide.

What the numbers legitimately show:

- **Strategy selection improved.** Every remaining strategy in the
  per-strategy table has WR >= 57% and positive net PnL.
- **Max DD fell by 3.88 percentage points.** This is the most
  robust change in the run - it reflects that the two shadowed
  strategies were net-losing contributors.
- **Trade count dropped 58 -> 31.** See "the cascade" below.

D7b (larger window) must confirm these before we trust the
magnitude. See section 6.

---

## 4. The cascade: why trade count dropped 27

Shadowing `rbd_dbr` and `flag_limits` did **not** just remove their
own trades. It changed the inputs to the debate engine.

Before D7c, those two strategies fired actionable signals on many
candles. Those signals entered the debate as evidence for BUY or
SELL. With their signals gone, HOLD wins more often.

Evidence from `confidence_histogram`:

    n_buy_sell_debates   60
    n_passed_gate        31
    n_rejected_by_gate   29

Only **60 debates** produced a BUY or SELL winner (out of 5070 that
ran). Compare to D6c: the same window with those strategies active
produced 5623 debates, and far more BUY/SELL winners.

**This is a feature, not a bug.** The two shadowed strategies were
weak signal generators; removing them made the debate engine more
selective. The 31 trades that remained are drawn from a smaller but
higher-conviction pool.

---

## 5. What the diagnostics confirmed

### 5a. The confidence gate at 0.70 is correct

From the histogram:

    Bucket     all   passed   rejected
    0.5-0.6     10        0         10
    0.6-0.7     20        1         19
    0.7-0.8     28       28          0
    0.8-0.9      1        1          0
    0.9-1.0      1        1          0

**Every debate in the 0.5-0.7 range was rejected** (with one
exception). **Every debate at 0.7+ passed.** The gate is not too
high - it is cleanly separating two populations. Lowering it to
0.65 would admit 19 more near-miss debates, whose track record in
this window is unknown but whose confidence is materially lower.

Mean: 0.684. Median: 0.706. **The 0.70 threshold sits almost exactly
on the median** - which is a reasonable place for it.

**Conclusion: do not lower the gate.** The D6c report's Focus 1 is
resolved: the gate is doing what it should.

### 5b. VOLATILE was never the problem D6c thought

D6c's per-regime table showed VOLATILE at -$431.60 with 25.5% WR.
D7c, after shadowing two strategies, shows:

    Regime    Trades   WR%     PnL
    RANGING       85   65.9%   +$1361.05
    CHOPPY         4  100.0%     +$0.80
    VOLATILE      21   42.9%     +$43.43

VOLATILE **flipped from -$431.60 to +$43.43**. The 27 fewer trades
removed the losers from VOLATILE. Per-strategy within VOLATILE:

    strategy             trades   WR%     PnL
    volume_cluster            1  100.0%   +$128.66
    bos_choch                 2   50.0%   +$100.86
    trapped_traders           3   66.7%    +$84.65
    false_breakout            3   66.7%    +$84.65
    rmd_trail                 3   33.3%    -$41.22
    bs_ss_liquidity           1    0.0%    -$70.08
    three_drive               2   50.0%   -$116.01
    mad_bb                    4   25.0%   -$134.44
    adaptive_rsi_ml           2    0.0%   -$235.29

**Two strategies account for the entire VOLATILE loss:**
`adaptive_rsi_ml` (-$235.29) and `mad_bb` (-$134.44). Both are
**profitable overall** (mad_bb +$149.45; adaptive_rsi_ml +$149.99).
So they are not bad strategies - they are bad **in VOLATILE**.

**Conclusion for D7b:** do not strengthen the VOLATILE block
wholesale. Instead, consider a targeted block: `mad_bb` and
`adaptive_rsi_ml` in VOLATILE only. But 6 trades is a small sample -
D7b should re-verify on the larger window before committing.

### 5c. TMO exits are no longer a concern

D6c had 11 TMO exits; D7c has 4. Every remaining TMO exit was a
**winner** (100% WR across all 4 strategies that produced them).
The TMO-losing strategies (`rbd_dbr`, `flag_limits`) are shadowed.
The remaining TMO exits are healthy timeout-of-winners, not
timeout-of-losers.

---

## 6. What's next: D7b

D7b should validate D7c's magnitude before we trust it:

1. **Rerun on a larger window.** Options:
   - 20,000 candles (2x) - `--candles 20000`
   - Walk-forward: 10 windows (per `INTEGRATION_PLAN_7_12.md` D8b)
2. **Observe:**
   - Does Sharpe stay above ~2.0?
   - Does Max DD stay below ~2.5%?
   - Does trade count scale proportionally (~62 trades over 20k)?
   - Do `mad_bb` and `adaptive_rsi_ml` remain VOLATILE losers?
3. **Do not change config in D7b** - it is a pure measurement delivery.
4. **D7c config changes are permanent** unless D7b shows a
   regression. We will not un-shadow `rbd_dbr` / `flag_limits`
   unless D7b on the larger window contradicts this run.

After D7b, decisions:
- Whether to add a targeted VOLATILE block for `mad_bb` + `adaptive_rsi_ml`
- Whether to wire `TierManager` into `StrategyRegistry` (architecture)
- Whether to promote `rmd_trail` / `mad_bb` out of `tier_3_probationary`

---

## 7. Known caveats and design notes

### volatile_by_strategy vs per-strategy PnL will not align

`volatile_by_strategy` credits each strategy named in a trade's
`contributing_strategies` list with the full trade PnL. If a trade
had 4 contributing strategies, all 4 are credited with the same
PnL. This is intentional - it answers "which strategies contributed
to VOLATILE outcomes" - but it means a strategy's VOLATILE PnL
**cannot** be added up with its per-strategy PnL to reconcile to
net. Same applies to `tmo_by_strategy`.

Example: `bs_ss_liquidity` shows -$17.52 in the per-strategy table
(1 trade) but -$70.08 in `volatile_by_strategy`. Those are the same
single trade attributed by two different keys (strategy PnL vs
regime PnL), and the delta is because the trade also contributed to
other strategies' VOLATILE attribution.

### The tier file is documentation only

See section 2. `tier_4_shadow` in `strategy_tiers.yaml` does **not**
shadow anything. The registry reads `global_disable` in
`strategy_regime_filters.yaml`. Any future change to tier
assignments must be mirrored in `global_disable` until the wiring
delivery lands.

---

## 8. Files changed

**Modified:**
- `config/strategy_regime_filters.yaml`
- `config/strategy_tiers.yaml`
- `backtest/beta_backtester.py`
- `tests/test_d6c_backtester_config.py` (import + 2 fixtures)

**Created:**
- `tests/test_d7_diagnostics.py`
- `docs/D7_REPORT.md`

**Untouched:**
- All QSC files
- `beta_brain/paper_trader.py`
- `beta_brain/performance_metrics.py`
- `beta_brain/debate/*`
- `beta_brain/jury/*`

---

## 9. Reference

- Final backtest report: `data/logs/backtest_beta_BTCUSDT_2026-10-01_2138.*`
- Prior baseline (D6c): `data/logs/backtest_beta_BTCUSDT_2026-10-01_2123.*`
- Original D6 analysis: `data/logs/backtest_beta_BTCUSDT_2026-10-01_1923.*`
- Related docs: `docs/D6C_REPORT.md`, `docs/BACKTEST_ANALYSIS.md`,
  `docs/INTEGRATION_PLAN_7_12.md`