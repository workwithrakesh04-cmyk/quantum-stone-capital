# Delivery 7b Report - 20k-Candle Validation of D7c

**Run date:** 2026-10-01
**Scope:** Validate D7c's config changes on 2x the data
**Status:** COMPLETE - D7c magnitude INVALIDATED; diagnostics captured
**QSC files touched:** none
**Config change:** NONE (D7b is pure measurement)

---

## 1. Headline: D7c did not hold

| Metric | D6c (10k) | D7c (10k) | **D7b (20k)** |
|---|---|---|---|
| Net PnL | +$1,233.91 (+12.34%) | +$1,458.48 (+14.58%) | **+$275.91 (+2.76%)** |
| Max DD | $622.10 (5.35%) | $167.87 (1.47%) | **$667.30 (6.56%)** |
| Trades | 58 | 31 | **54** |
| Win rate | 51.72% | 64.52% | **50.00%** |
| Profit factor | 1.587 | 3.028 | **1.165** |
| Expectancy/trade | +$21.27 | +$47.05 | **+$5.11** |
| Sharpe | 1.08 | 4.84 | **0.17** |
| Sortino | 1.65 | 9.10 | **0.25** |
| Calmar | 2.31 | 9.92 | **0.42** |
| Exits TP/SL/TMO/EOD | 22/25/11/0 | 13/14/4/0 | 18/24/12/0 |

**D7c's Sharpe 4.84 was a small-sample artifact.** On 2x the
data, the same config produces Sharpe **0.17**.

The honest reading:

- **D6c (Sharpe 1.08, 58 trades)** was a weak but real signal.
- **D7c (Sharpe 4.84, 31 trades)** was a lucky window.
- **D7b (Sharpe 0.17, 54 trades)** is the truth on this data.

D7b was designed to catch exactly this. It caught it. The D7c
config changes (shadowing `rbd_dbr` + `flag_limits`) are **not
validated as an improvement** on risk-adjusted returns.

---

## 2. What D7b confirmed (positive findings)

### 2a. The 0.70 confidence gate is correct

Histogram on 20k data:

    Bucket     all   passed   rejected
    0.5-0.6     20        0         20
    0.6-0.7     35        5         30
    0.7-0.8     49       49          0
    0.8-0.9      1        1          0
    0.9-1.0      3        3          0

Mean: 0.685. Median: 0.682.

**The 0.70 gate cleanly separates the two populations.** On the
larger sample, 5 of the 0.6-0.7 debates passed (vs 1 on 10k) - the
gate is not a hard wall, but the boundary is well-placed.
**Do not lower it.**

### 2b. The 60-minute TMO is correct

12 TMO exits on 20k, and every strategy's TMO sum is positive:

    strategy             TMO count   WR%    PnL
    trapped_traders          7      85.7%   +$271.51
    false_breakout           7      85.7%   +$271.51
    mad_bb                   5     100.0%   +$316.50
    liquidity_sweep          6      83.3%   +$166.94
    rmd_trail                3     100.0%   +$254.75
    bos_choch                4     100.0%   +$204.19
    adaptive_rsi_ml          4     100.0%   +$204.19
    three_drive              2     100.0%   +$135.01
    volume_cluster           1     100.0%   +$112.31
    ichimoku_rsi             1     100.0%    +$31.31

**The 60-min timeout is not closing losers.** The TMO-losers D6c
identified (`rbd_dbr`, `flag_limits`) are shadowed. What remains
is healthy "winner timed out before TP" behavior.
**Leave the timeout at 60 min.**

### 2c. `adaptive_rsi_ml` is a consistent VOLATILE loser

| Strategy | 10k VOLATILE | **20k VOLATILE** |
|---|---|---|
| adaptive_rsi_ml | -$235.29 (0% WR, 2 trades) | **-$267.47 (0% WR, 3 trades)** |
| bos_choch | +$100.86 | **+$113.90** |
| false_breakout | +$84.65 | **+$71.32** |
| mad_bb | -$134.44 (25% WR, 4 trades) | **+$15.20 (33% WR, 6 trades)** |
| liquidity_sweep | -- | -$110.35 (0% WR, 1 trade) |
| bs_ss_liquidity | -$70.08 | -$62.85 |

**`adaptive_rsi_ml` loses in VOLATILE on both samples** (0% WR,
2 and 3 trades respectively, net -$502.76 combined). This is a
real, consistent signal.

**`mad_bb` flipped positive** on 20k, so it should NOT be blocked
in VOLATILE.

**A targeted VOLATILE block for `adaptive_rsi_ml` only** is the
evidence-backed change if we choose to make one. It would need
verification on a walk-forward.

---

## 3. What D7b invalidated

### 3a. D7c's magnitude

Sharpe 4.84 -> 0.17. PnL +14.58% -> +2.76%. Max DD 1.47% -> 6.56%.

**Do not cite D7c's metrics as stable.** Do not cite D7c's win
rate of 64.52% as an improvement over D6c's 51.72%. Both were
one-window artifacts.

### 3b. The hope that the D7c config change is a large improvement

It is not. The strategy set, on 70 days of data, is essentially
flat on a risk-adjusted basis. The config change may still be
slightly beneficial (it removed two consistently-negative
strategies) but its effect is within noise.

---

## 4. What D7b leaves open

### 4a. Should `rbd_dbr` + `flag_limits` stay shadowed?

**Recommendation: YES.** Reasons:

- D6c (10k) showed both were net-negative: -$124.64 and -$28.60.
- Across D6c + D7b, both are consistently negative contributors.
- D7b's overall weakness is not caused by their shadowing -
  D7b's weakness is that the whole strategy set is flat. If we
  un-shadowed them, D7b would likely look worse, not better.
- There is no run in which either was net positive across the
  whole window.

**But flag for revisit:** if D8b (walk-forward) shows either
strategy positive in some regime, promotion back is possible.

### 4b. What to do about CHOPPY?

**NEW finding, not visible on 10k (D6c had 4 CHOPPY trades).**

    Regime      Trades   WR%     PnL       Avg
    RANGING        146   56.2%   +$398.26   +$2.73
    CHOPPY          21   19.0%   -$146.24   -$6.96
    VOLATILE        29   20.7%   -$161.63   -$5.57

**CHOPPY is a net loser on 20k.** 21 trades, 19% WR, -$146.24.
D6c's CHOPPY sample was too small to judge (4 trades). This is a
new finding.

Options for a future delivery:
- Block new trades entirely in CHOPPY
- Block specific strategies in CHOPPY (need per-strategy CHOPPY
  attribution, which we don't currently collect - could add in
  D7d)
- Leave it; -$146 on $10k starting balance is a -1.46% drag

The full 3-regime picture on 20k: RANGING makes +$398, CHOPPY loses
-$146, VOLATILE loses -$162. **The strategy set makes money in
RANGING and loses it elsewhere.**

### 4c. Is the strategy set's edge real but small, or curve-fit?

**Cannot be determined from one window.** This is the fundamental
limit of the D7b design. The right next step is walk-forward (D8b):
run 10 non-overlapping windows and see if RANGING edge holds and
whether CHOPPY / VOLATILE losses are consistent.

---

## 5. The honest bottom line

The strategy set, on 70 days of BTCUSDT 5m:

- **+2.76% net PnL**
- **6.56% max drawdown**
- **50% win rate**
- **Sharpe 0.17**
- **Profit factor 1.165**

This is a **flat system on a risk-adjusted basis.** Not
unprofitable - the net is positive - but the edge is thin enough
that the next delivery's decisions must be based on real signal,
not single-window backtests.

**D7b's value is that it tells us this cleanly.** If we had
stopped at D7c and shipped it, we would have believed the system
had Sharpe 4.84. That would have been a costly mistake.

---

## 6. What's next

Three candidates for the next delivery, in order of recommendation:

### Recommended: D8b - walk-forward validation

Per `docs/INTEGRATION_PLAN_7_12.md`, D8b is walk-forward on 10
windows. It answers the question D7b cannot: **is the RANGING edge
consistent, or was it one period of luck?**

Files needed:
- `backtest/walk_forward_beta.py` (new - walk-forward harness)
- `tests/test_walk_forward_beta.py`
- No config changes

This is a real delivery (~2-3 paste blocks) but it's the correct
next step. Every backtest so far has been a single window, and
D7b just proved single windows mislead.

### Alternative: D7d - targeted VOLATILE block

Small, evidence-backed from D7b: block `adaptive_rsi_ml` in
VOLATILE only. Adds ~1 line to `strategy_regime_filters.yaml`.
But its effect will likely be within noise (3 VOLATILE trades
over 20k).

### Later: D8 - shadow trading

The original plan. Write outcomes to JSONL so the trainer can
learn. Infrastructure work, not a validation step.

**Recommendation: D8b walk-forward first.** D7b proved the single-
window approach cannot validate anything. Until we have
walk-forward, we are guessing at which strategies have edge.

---

## 7. Files changed

**Created:**
- `docs/D7B_REPORT.md` (this file)

**Modified:**
- `docs/BACKTEST_ANALYSIS.md` (D7b section appended)
- `docs/BETA_BRAIN.md` (Delivery 7b entry appended)
- `docs/RESUME_PROMPT.md` (Current State updated)

**Not changed:**
- All source code
- All config
- QSC files

D7b is measurement only. No config or code change.

---

## 8. Reference

- D7b backtest report: `data/logs/backtest_beta_BTCUSDT_2026-10-01_2157.*`
- D7c backtest report: `data/logs/backtest_beta_BTCUSDT_2026-10-01_2138.*`
- D6c backtest report: `data/logs/backtest_beta_BTCUSDT_2026-10-01_2123.*`
- D6 backtest report: `data/logs/backtest_beta_BTCUSDT_2026-10-01_1923.*`
- Related docs: `docs/D7_REPORT.md`,
  `docs/D6C_REPORT.md`, `docs/BACKTEST_ANALYSIS.md`,
  `docs/INTEGRATION_PLAN_7_12.md`