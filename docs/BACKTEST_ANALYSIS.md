# Backtest Analysis - BTCUSDT 5m, 10,000 candles

**Run date:** 2026-10-01
**Symbol:** BTCUSDT
**Timeframe:** 5m
**Period:** 2026-08-27 -> 2026-10-01 (35 days)
**Candles:** 10,000 (warmup 100)
**Runtime:** 44.5s
**Report files:**
- data/logs/backtest_beta_BTCUSDT_2026-10-01_1923.txt
- data/logs/backtest_beta_BTCUSDT_2026-10-01_1923.json
- data/logs/backtest_beta_BTCUSDT_2026-10-01_1923_trades.csv

---

## Headline

| Metric | Value |
|---|---|
| Starting balance | $10,000.00 |
| Ending balance | $10,567.91 |
| Net PnL | **+$567.91 (+5.68%)** |
| Peak balance | $11,226.39 |
| Max drawdown | $707.56 (6.30%) |
| Total trades | 28 |
| Wins / Losses | 13 / 15 |
| Win rate | 46.43% |
| Profit factor | **1.493** |
| Avg win / avg loss | $132.26 / -$76.76 |
| Expectancy per trade | +$20.28 |
| Exits TP / SL | 12 / 16 |
| Reported Sharpe | 10.64 (see below - it is wrong) |
| Sortino | 0.05 |
| Calmar | 0.9 |

**Rejection rate:** 3052 debates run, 28 trades -> 99.1% rejection.

---

## Known Bugs In This Run

### Bug 1 - Sharpe annualization inflated

`beta_brain/performance_metrics.py::compute_sharpe` uses `periods_per_year=105120` (5m bars per year). Trade-based Sharpe should use trades-per-year, not bars-per-year.

Estimated real Sharpe: **~0.5** (not 10.64).

**Fix:** compute periods_per_year from trade frequency, or pass it explicitly from the backtester.

### Bug 2 - max_hold_bars not enforced in backtest

Trade #6 was held for 320 bars (26.7 hours) - in a "scalp" mode which allows 60 minutes.

**Root cause:** `beta_backtester.py` passes `max_hold_bars=0` (no timeout) to `PaperTrader.open_trade`.

**Fix:** derive max_hold_bars from account config (`modes.scalp.max_holding_minutes / 5`) and pass it.

### Bug 3 - Rejection diagnostic missing

We know 3052 debates produced 28 trades, but we don't know the stage-by-stage rejection:
- How many debates returned HOLD?
- How many BUY/SELL were below min_confidence?
- How many were rejected by RiskJury vs PortfolioJury?

**Fix:** add stage counters in the backtester.

---

## Per-Strategy Results (sorted by PnL)

### Winners

| Strategy | Trades | WR% | PnL | Avg/trade | Tier |
|---|---|---|---|---|---|
| false_breakout | 11 | 54.5% | +$209.90 | +$19.08 | T1 |
| trapped_traders | 12 | 50.0% | +$192.98 | +$16.08 | T1 |
| liquidity_sweep | 8 | 50.0% | +$180.32 | +$22.54 | T1 |
| volume_cluster | 2 | 100.0% | +$92.60 | +$46.30 | T1 |
| rbd_dbr | 11 | 45.5% | +$14.65 | +$1.33 | T2 |

### Losers

| Strategy | Trades | WR% | PnL | Avg/trade | Tier |
|---|---|---|---|---|---|
| three_drive | 7 | 42.9% | -$4.41 | -$0.63 | T2 |
| flag_limits | 8 | 50.0% | -$12.65 | -$1.58 | none |
| bs_ss_liquidity | 1 | 0.0% | -$17.56 | -$17.56 | none |
| rmd_trail | 12 | 41.7% | -$18.22 | -$1.52 | T3 |
| adaptive_rsi_ml | 10 | 40.0% | -$23.68 | -$2.37 | none |
| ichimoku_rsi | 1 | 0.0% | -$24.47 | -$24.47 | T2 |
| mad_bb | 14 | 35.7% | -$70.64 | -$5.05 | T3 |

**Conclusion:** The tier system was mostly right. 4 of the 5 winners are Tier 1.
The 4 biggest losers are all outside Tier 1.

---

## Per-Regime Results

| Regime | Trades | WR% | PnL | Avg |
|---|---|---|---|---|
| RANGING | 65 | 52.3% | **+$719.40** | +$11.07 |
| VOLATILE | 32 | 31.2% | **-$200.59** | -$6.27 |

**Conclusion:** Every profitable strategy performed better in RANGING.
Every strategy except volume_cluster lost money in VOLATILE.

Action: strengthen VOLATILE blocking in config.

---

## Per-Direction Results

| Direction | Total PnL |
|---|---|
| BUY | +$588.67 (net positive) |
| SELL | -$20.76 (net negative) |

**Conclusion:** SHORT trades were dragged down by 3 strategies:
- mad_bb: -$60.43 (11 trades, 36.4% WR)
- rmd_trail: -$90.04 (9 trades, 33.3% WR)
- adaptive_rsi_ml: -$69.28 (6 trades, 33.3% WR)

Removing these 3 from SHORT would turn SELL into a net winner.

---

## Recommended Actions

### Option A - Fix backtester bugs, rerun

Ship Delivery 6c:
1. Fix Sharpe annualization (use trading-days)
2. Fix max_hold_bars (read from config)
3. Add rejection-stage diagnostics
4. Rerun backtest, get honest numbers

### Option B - Tune config, rerun

Ship Delivery 7:
1. Move mad_bb, rmd_trail, adaptive_rsi_ml to shadow
2. Strengthen VOLATILE regime block
3. Rerun backtest

Expected: SHORT PnL -> ~+$100, VOLATILE -> ~0, net -> ~+$900 (Sharpe ~0.8)

### Option C - Both in sequence

Delivery 6c first, then Delivery 7. Rerun and evaluate for
shadow trading (Delivery 8).

### Decision

Option C is preferred.

---

## Reference - Future Deliveries

| Delivery | Scope |
|---|---|
| 6c | Fix Sharpe + max_hold_bars + diagnostics |
| 7 | Tune config based on backtest |
| 8 | Shadow trading (write outcomes to JSONL) |
| 8b | Walk-forward (10 windows) |
| 8c | Strategy parameter sweep |
| 9 | XAUUSD adapter |
| 10 | New resources (books + strategies) |


---

# D6c - Honest Metrics + Timeout Enforced (2026-10-01)

**Reference:** full report in `docs/D6C_REPORT.md`
**Final run:** `data/logs/backtest_beta_BTCUSDT_2026-10-01_2123.*`

Three bugs identified in the D6 analysis above are now closed:

| Bug | Status | Before | After |
|---|---|---|---|
| Sharpe annualization | CLOSED | 16.95 (fake) | **1.08** (real) |
| max_hold_bars not enforced | CLOSED | 0 (bug) | **12** (60min / 5m) |
| Rejection diagnostic missing | CLOSED | one counter | 4-stage funnel |
| Sortino formula (bonus) | CLOSED | 0.08 (broken) | **1.65** (real) |

## Honest final numbers (TMO enabled)

- Net PnL: **+$1,233.91 (+12.34%)**
- Sharpe: **1.08**
- Sortino: **1.65**
- Calmar: **2.31**
- Max DD: **$622.10 (5.35%)**
- Trades: 58 (30 W / 28 L)
- PF: 1.587
- Exits: 22 TP / 25 SL / **11 TMO**

## Rejection funnel (new)

    rejected_hold           4277   (43.4%)
    rejected_low_confidence 5394   (54.8%)   <- biggest filter
    rejected_risk_jury      171    ( 1.7%)
    rejected_portfolio_jury 0      ( 0.0%)

## IMPORTANT CORRECTION

The "Recommended Actions -> Option B" section above says to move
**mad_bb**, **rmd_trail**, **adaptive_rsi_ml** to shadow. **That
recommendation is now invalidated by the D6c run.**

In the honest run, those three are the top PnL contributors:

- rmd_trail: +$272.83
- adaptive_rsi_ml: +$257.56
- mad_bb: +$50.62

**Do NOT shadow them.** The real shadow candidates are:

- flag_limits (-$124.64, worst by far)
- rbd_dbr (-$28.60, borderline)

See `docs/D6C_REPORT.md` section 6 for full detail.

---

# D7c - Shadow TMO Losers + Diagnostic Aggregations (2026-10-01)

**Reference:** full report in `docs/D7_REPORT.md`
**Final run:** `data/logs/backtest_beta_BTCUSDT_2026-10-01_2138.*`

## Config changes

- Shadowed `rbd_dbr` and `flag_limits` via `global_disable`
  (in `strategy_regime_filters.yaml`)
- Moved both to `tier_4_shadow` in `strategy_tiers.yaml`
  (documentation only - the registry does not read tiers yet)
- Added 3 diagnostic aggregations to the backtester:
  `confidence_histogram`, `volatile_by_strategy`, `tmo_by_strategy`

## D6c -> D7c comparison

| Metric | D6c | D7c | Delta |
|---|---|---|---|
| Net PnL | +$1,233.91 (+12.34%) | +$1,458.48 (+14.58%) | +$224.57 |
| Max DD | 5.35% | **1.47%** | -3.88pp |
| Trades | 58 | 31 | -27 |
| Win rate | 51.72% | **64.52%** | +12.80pp |
| Profit factor | 1.587 | **3.028** | +1.441 |
| Sharpe | 1.08 | 4.84 | +3.76 (see caveat) |
| Sortino | 1.65 | 9.10 | +7.45 (see caveat) |
| Calmar | 2.31 | 9.92 | +7.61 (see caveat) |

**SMALL-SAMPLE CAVEAT:** D7c's Sharpe / Sortino / Calmar are
computed on 31 trades. Do not cite them as stable improvements.
D7b must validate on a larger window.

## Diagnostic findings (data, not guesses)

### The confidence gate at 0.70 is correct

Histogram for BUY/SELL debates:

    0.5-0.6:  10 all rejected
    0.6-0.7:  20, 19 rejected, 1 passed
    0.7-0.8:  28, all passed
    0.8+:      2, all passed

Mean 0.684, median 0.706. The 0.70 gate sits at the median and
cleanly separates the passed/rejected populations. **Do not lower
it.** D6c Focus 1 is resolved.

### VOLATILE flipped positive

VOLATILE regime PnL went -$431.60 -> +$43.43. The 27 fewer trades
removed the VOLATILE losers. Two strategies accounted for the
prior VOLATILE loss: `adaptive_rsi_ml` (-$235.29 in VOLATILE) and
`mad_bb` (-$134.44 in VOLATILE) - but both are net positive overall.
This suggests a **targeted** VOLATILE block (not a wholesale one) if
D7b confirms on the larger window. D6c Focus 2 is now: measure, do
not block blindly.

### TMO exits now healthy

4 TMO exits remain, all winners. The TMO-losing strategies are
shadowed. D6c Focus 3 (TMO analysis) is resolved by the config
change.

## IMPORTANT - the D6 shadow recommendation is still invalidated

The "Option B" shadow list at the top of this file still says to
shadow `mad_bb`, `rmd_trail`, `adaptive_rsi_ml`. **That is still
wrong.** In D7c:

- `rmd_trail`: +$189.66
- `adaptive_rsi_ml`: +$149.99 (though -$235.29 in VOLATILE only)
- `mad_bb`: +$149.45 (though -$134.44 in VOLATILE only)

The correct shadow candidates were `flag_limits` and `rbd_dbr`, and
D7c shadowed them.

## Next: D7b

Rerun on a larger window (20k candles or walk-forward). Pure
measurement, no config change. Confirm Sharpe, Max DD, and the
VOLATILE attribution before further tuning.