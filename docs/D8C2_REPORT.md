# Delivery 8c-2 Report - Shadow volume_cluster + Hard Stop Implementation

**Run date:** 2026-10-02
**Scope:** Prune to 3 active strategies; implement (but do not yet wire) per-window hard stop
**Status:** PARTIAL PASS - 3 of 4 criteria met; DD remains the sole gap
**QSC files touched:** none

---

## 1. Headline

D8c-2 shadowed `volume_cluster` (the last weak strategy) and
implemented the per-window hard stop in `BetaBacktester`. The hard
stop is NOT yet wired into the walk-forward runner - that is D8c-3.

Result on the same 20k-candle walk-forward:

| # | Criterion | D8c | D8c-2 | Pass? |
|---|-----------|-----|-------|-------|
| 1 | Chained equity positive | +1.81% | **+2.86%** | YES |
| 2 | Median Sharpe >= 1.0 | +1.085 | **+1.045** | YES |
| 3 | Sharpe pos windows >= 7/10 | 6/10 | **7/10** | YES |
| 4 | Max window DD <= 5% | 9.01% | **9.01%** | NO |

**3 of 4.** The remaining fail is the max window drawdown, and
D8c-2's data pinpoints exactly where it comes from.

---

## 2. What improved

### 2a. Chained equity up again

    D8b:   $10000 -> $9771    (-2.29%)
    D8c:   $10000 -> $10181   (+1.81%)
    D8c-2: $10000 -> $10286   (+2.86%)

Three consecutive improvements.

### 2b. Positive-Sharpe windows crossed the threshold

    D8c:   6/10
    D8c-2: 7/10  <- crossed our pass line

### 2c. Positive-return windows rose to 8/10

    return_pct_positive_windows: 8

Eight of ten windows were net positive. The two negative ones
(window 3 and window 5) account for the entire loss.

### 2d. Per-strategy consistency is 80%

    trapped_traders   80.0% pos, 108 trades, +$345.18
    liquidity_sweep   80.0% pos, 108 trades, +$345.18
    false_breakout    80.0% pos, 108 trades, +$345.18

**IMPORTANT INTERPRETATION CAVEAT:** these three strategies have
*identical* trade counts and PnL because they fire on almost
every trade together (they are correlated RANGING-mean-reversion
strategies). This is not three independent edges; it is one
signal credited three times. The system is effectively a single
RANGING strategy, not a portfolio of three.

---

## 3. The DD problem: window 3

Per-window table:

    #   Trades  WR%    PnL$      Ret%     DD%    Sharpe
    1     10   60.0%   +40.98   +0.41%   2.14%    +0.09
    2     10   50.0%  +276.12   +2.76%   2.50%    +3.93
    3     10   10.0%  -901.43   -9.01%   9.01%   -24.32   <-- the problem
    4     15   66.7%  +394.45   +3.94%   1.44%    +5.25
    5     15   26.7%  -186.13   -1.86%   4.67%    -2.05
    6      6   66.7%  +221.71   +2.22%   0.95%    +1.80
    7      6   50.0%  +178.25   +1.78%   2.76%    +4.49
    8     14   50.0%    +7.88   +0.08%   3.41%    +0.42
    9     11   45.5%  +239.47   +2.39%   3.21%    -3.89
   10     11   45.5%   +73.88   +0.74%   3.53%    +1.67

**Window 3 lost 10% of its trades:** 1 win, 9 losses, -$901.43.
Every other window is between -1.86% and +3.94%. Removing window
3 from the chained curve would give a system with no DD over 5%.

The 9.01% max DD is **entirely** window 3. Shadowing
`volume_cluster` did not change it because `volume_cluster` was
not involved in the window-3 drawdown.

**This is exactly what the D8c-3 hard stop is designed to fix.**

---

## 4. What D8c-2 did not do

The hard stop is **implemented but not yet called**:

- `BetaBacktester.__init__` accepts `window_hard_stop_pct: float = 0.0`
- `run_on_candles` checks it after each `process_candle`; if
  cumulative return <= -threshold, it calls
  `close_all_at_price` and sets `self._window_halted = True`
- Tests: `tests/test_d8c2_hard_stop.py` (13 tests)
- `get_diagnostics()` now reports `window_hard_stop_pct`,
  `window_halted`, `halt_candle_idx`

But `WalkForwardRunner._run_one_window` does not pass this value,
and `scripts/walk_forward_beta.py` has no CLI flag for it. So this
run exercised the pruning change only.

**D8c-3 wires it.**

---

## 5. Config changes

Shadowed in D8c-2:

    volume_cluster    42.9% pos, 12 trades, -$30.43

Full active list after D8c-2 (3 strategies):

    false_breakout
    trapped_traders
    liquidity_sweep

All three are Tier 1. `global_disable` now holds 34 strategies;
`tier_4_shadow` holds 34. Only 3 strategies are active.

---

## 6. Where this leaves the system

Improvements in three straight deliveries:

| Metric | D8b | D8c | D8c-2 |
|--------|-----|-----|-------|
| Chained equity | -2.29% | +1.81% | **+2.86%** |
| Sharpe pos wins | 5/10 | 6/10 | **7/10** |
| Median Sharpe | -0.575 | +1.085 | **+1.045** |
| Max window DD | 10.80% | 9.01% | 9.01% |
| Active strategies | 12 | 4 | 3 |

The system has flipped to consistently profitable. **The one
remaining gap is a single bad window.**

## 7. What's next: D8c-3

Wire `window_hard_stop_pct` through the walk-forward runner and
CLI. Rerun at `--window-hard-stop 3.0`. Expected outcome: window
3 halts at roughly -3% instead of running to -9%, cutting the
worst DD by two-thirds.

If D8c-3 passes all four criteria, the strategy set has earned a
shot at D8 shadow trading.

If D8c-3 fails, the 9% DD is structural (not stop-level), and
the conclusion is that these three correlated strategies cannot
be made drawdown-safe by a stop alone.

---

## 8. Files changed

**Modified:**
- `backtest/beta_backtester.py` - added `window_hard_stop_pct`
  parameter, halt logic in `run_on_candles`, 3 new diagnostics
  fields
- `config/strategy_regime_filters.yaml` - `volume_cluster` added
  to `global_disable`
- `config/strategy_tiers.yaml` - `volume_cluster` added to
  `tier_4_shadow`
- `docs/BETA_BRAIN.md` - D8b commit note added

**Created:**
- `tests/test_d8c2_hard_stop.py` (13 tests)
- `docs/D8C2_REPORT.md` (this file)

**Not changed:**
- All QSC files
- `beta_brain/`

---

## 9. Reference

- D8c-2 walk-forward: `data/logs/walk_forward_beta_BTCUSDT_2026-10-02_2157.*`
- D8c baseline: `data/logs/walk_forward_beta_BTCUSDT_2026-10-02_2049.*`
- D8b baseline: `data/logs/walk_forward_beta_BTCUSDT_2026-10-01_2214.*`
- Related docs: `docs/D8C_REPORT.md`, `docs/D8B_REPORT.md`