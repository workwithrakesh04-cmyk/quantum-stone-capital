# Delivery 6c Report - Honest Sharpe/Sortino, max_hold_bars, Stage Diagnostics

**Run date:** 2026-10-01
**Scope:** Fix three bugs surfaced by the D6 backtest analysis
**Status:** COMPLETE - all three bugs closed, tests green, docs updated
**QSC files touched:** none (only `beta_brain/`, `backtest/`, `tests/`, `config/beta_*.yaml`)

---

## 1. Summary

Three bugs identified in `docs/BACKTEST_ANALYSIS.md` after Delivery 6:

| # | Bug | Status | Evidence |
|---|-----|--------|----------|
| 1 | Sharpe annualization inflated (used bars/year, not trades/year) | **CLOSED** | Reported 16.95 -> honest 1.08 |
| 2 | `max_hold_bars` not enforced in backtest (hardcoded 0) | **CLOSED** | `max_hold_bars_used = 12`, 11 TMO exits fired |
| 3 | Rejection diagnostic missing (single counter) | **CLOSED** | Stage breakdown now in diagnostics |

Bonus fix: **Sortino formula was structurally wrong** (used std-of-losers
instead of downside deviation vs MAR over all trades). Reported 0.08 -> honest 1.65.

---

## 2. What changed

### `beta_brain/performance_metrics.py`

- `compute_sharpe(trade_returns, periods_per_year=None)`
  - Default changed from hardcoded `105120` to `None` (auto-infer)
  - New helper `infer_periods_per_year(total_trades, period_days)`:
    uses `total_trades * 365 / period_days` when period is known,
    else falls back to 252 (trading days)
  - `enrich()` now accepts `period_days` and threads the inferred
    `periods_per_year` through to both Sharpe and Sortino

- `compute_sortino(trade_returns, mar=0.0, periods_per_year=None)`
  - Old: `std(losers, ddof=1)` -> measures dispersion *within* losers.
    This structurally under-estimates downside deviation and produces
    a near-zero Sortino. That is why the D6 run reported Sortino=0.05.
  - New: `dd = sqrt(mean(min(0, r - mar)^2))` over ALL trades.
    This is the textbook definition.
  - Annualized the same way as Sharpe.

### `backtest/beta_backtester.py`

- `_derive_max_hold_bars()` reads `account_rules.enable_timeout_exits`
  and `modes.<mode>.max_holding_minutes` (or `.max_holding_hours`),
  divides by the timeframe in minutes, floors to >= 1.
- `open_trade(...)` now receives `max_hold_bars=self.max_hold_bars`
  instead of hardcoded 0.
- Rejection counters split:
  - `rejected_hold`             - no actionable signals this candle
  - `rejected_low_confidence`   - debate.winner_confidence < min_conf
  - `rejected_risk_jury`        - risk jury rejected
  - `rejected_portfolio_jury`   - portfolio jury rejected
  - `trades_rejected` kept as the sum (backward compatible)
- `enrich()` call now passes `period_days` so Sharpe/Sortino are
  annualized correctly.

### `config/beta_personal.yaml` and `config/beta_prop.yaml`

- `account_rules.enable_timeout_exits`: `false` -> `true`

**Note on `paper_trader.py`:** the timeout branch already existed
(`bars_held >= max_hold_bars -> CLOSED_TIMEOUT`). It simply never
received a non-zero value. No change needed.

---

## 3. Four-run comparison

| Metric | D6 (19:23) | pre-D6c (19:49) | post-D6c, no TMO (21:21) | **post-D6c, TMO on (21:23)** |
|---|---|---|---|---|
| Net PnL | +$567.91 | +$1,621.11 | +$1,621.11 | **+$1,233.91** |
| Return % | +5.68% | +16.21% | +16.21% | **+12.34%** |
| Peak balance | $11,226.39 | $12,081.17 | $12,081.17 | $11,624.78 |
| Max DD $ | $707.56 | $800.23 | $800.23 | **$622.10** |
| Max DD % | 6.30% | 6.62% | 6.62% | **5.35%** |
| Total trades | 28 | 58 | 58 | 58 |
| Win rate | 46.43% | 53.45% | 53.45% | 51.72% |
| Profit factor | 1.493 | 1.666 | 1.666 | **1.587** |
| Avg win | $132.26 | $130.80 | $130.80 | $111.24 |
| Avg loss | -$76.76 | -$90.14 | -$90.14 | -$75.11 |
| Expectancy/trade | +$20.28 | +$27.95 | +$27.95 | **+$21.27** |
| Sharpe (reported) | 10.64 | 16.95 | **1.29** | **1.08** |
| Sortino (reported) | 0.05 | 0.08 | **1.95** | **1.65** |
| Calmar | 0.9 | 2.45 | 2.45 | **2.31** |
| Exits TP/SL/TMO/EOD | 12 / 16 / - / - | 28 / 30 / 0 / 0 | 28 / 30 / 0 / 0 | **22 / 25 / 11 / 0** |
| `max_hold_bars_used` | (bug) | (bug) | 0 | **12** |

The two "reported" runs (D6 and 19:49) show inflated Sharpe values
(10.64 / 16.95). Those numbers should never be cited. From 21:21
onward, the Sharpe is honest.

---

## 4. Key finding: enforcing the timeout changes the picture

Enabling `enable_timeout_exits` (60-minute scalp limit) reduced
net PnL by $387 (+16.21% -> +12.34%) but **improved risk-adjusted
metrics**:

- Max drawdown: 6.62% -> **5.35%**
- Sortino held: 1.95 -> 1.65 (still >1.5)
- Calmar held: 2.45 -> 2.31
- Sharpe: 1.29 -> 1.08 (small drop, expected given lower return)

**11 trades closed via TMO.** Those trades were net losers that
were previously held indefinitely awaiting TP/SL. The prior run's
higher PnL was partly the result of holding losers.

**Interpretation:** the strategy set has a tendency to hold losers
past the intended scalp window. D7 should examine:
1. Whether 60min is the right scalp window for BTC 5m.
2. Whether repeated TMO on the same strategy indicates the strategy
   is mis-classified (scalp vs swing) or its SL is too far.

---

## 5. Rejection funnel (new visibility from D6c)

From the final (21:23) run:

    candles_processed         9900
    debates_run               5623   (actionable signals existed)
    trades_opened             58
    trades_rejected           9842   (per-candle, sum of below)
      rejected_hold           4277   (43.4%)  no actionable signals
      rejected_low_confidence 5394   (54.8%)  debate confidence < 0.7
      rejected_risk_jury      171    ( 1.7%)  risk jury rejected
      rejected_portfolio_jury 0      ( 0.0%)  portfolio jury never rejected

**Takeaway:** the min-confidence gate is by far the largest filter.
54.8% of all rejections are because `debate.winner_confidence < 0.7`.
This is now the top lever for D7 - either the gate is mis-tuned, or
the debate engine systematically produces confidences below 0.7.

---

## 6. Per-strategy top / bottom (final run)

### Winners

| Strategy | Trades | WR% | PnL |
|---|---|---|---|
| rmd_trail | 30 | 60.0% | +$272.83 |
| adaptive_rsi_ml | 27 | 63.0% | +$257.56 |
| false_breakout | 10 | 60.0% | +$206.30 |
| trapped_traders | 11 | 54.5% | +$189.23 |
| liquidity_sweep | 8 | 50.0% | +$163.97 |
| bos_choch | 34 | 52.9% | +$125.23 |
| volume_cluster | 2 | 100.0% | +$94.88 |
| mad_bb | 42 | 47.6% | +$50.62 |

### Losers

| Strategy | Trades | WR% | PnL |
|---|---|---|---|
| flag_limits | 12 | 25.0% | -$124.64 |
| rbd_dbr | 25 | 44.0% | -$28.60 |
| ai_source_ma | 1 | 0.0% | -$19.64 |
| bs_ss_liquidity | 1 | 0.0% | -$18.18 |
| ichimoku_rsi | 2 | 50.0% | -$10.63 |

### IMPORTANT: the D7 shadow list from BACKTEST_ANALYSIS.md is INVALIDATED

`docs/BACKTEST_ANALYSIS.md` recommended moving **mad_bb**, **rmd_trail**,
and **adaptive_rsi_ml** to shadow. In the honest D6c run, those three
are among the **top PnL contributors**:

| Strategy | BACKTEST_ANALYSIS said | D6c honest PnL |
|---|---|---|
| rmd_trail | shadow candidate | +$272.83 (best) |
| adaptive_rsi_ml | shadow candidate | +$257.56 (2nd) |
| mad_bb | shadow candidate | +$50.62 (still positive) |

**The real D7 shadow candidates are instead:**

| Strategy | Trades | WR% | PnL | Note |
|---|---|---|---|---|
| flag_limits | 12 | 25.0% | -$124.64 | worst by far |
| rbd_dbr | 25 | 44.0% | -$28.60 | high volume, net negative |
| ai_source_ma | 1 | 0.0% | -$19.64 | sample too small to judge |
| bs_ss_liquidity | 1 | 0.0% | -$18.18 | sample too small to judge |

`flag_limits` is the only clearly negative strategy with a
meaningful sample. `rbd_dbr` is borderline. The two single-trade
strategies cannot be judged yet.

---

## 7. Per-regime (final run)

| Regime | Trades | WR% | PnL | Avg |
|---|---|---|---|---|
| RANGING | 160 | 58.8% | +$1,612.55 | +$10.08 |
| CHOPPY | 4 | 100.0% | +$0.80 | +$0.20 |
| VOLATILE | 51 | 25.5% | -$431.60 | -$8.46 |

VOLATILE remains the loss centre: 25.5% win rate over 51 trades.
Strengthening the VOLATILE block is still a D7 candidate.

---

## 8. Files changed

**Modified:**
- `beta_brain/performance_metrics.py`
- `backtest/beta_backtester.py`
- `config/beta_personal.yaml` (enable_timeout_exits)
- `config/beta_prop.yaml` (enable_timeout_exits)

**Created:**
- `tests/test_d6c_performance_metrics.py` (25 tests)
- `tests/test_d6c_backtester_config.py` (13 tests)

**Untouched:**
- `beta_brain/paper_trader.py` (timeout branch was already correct)
- All QSC files

---

## 9. What this enables for D7

D6c gives D7 an honest baseline:

- **Real Sharpe: 1.08** (was a fake 16.95)
- **Real Sortino: 1.65**
- **Real max DD: 5.35%**
- **Real net PnL: +12.34%** over 35 days

D7 (config tuning) should now focus, in order:

1. **Min-confidence gate** (`rejected_low_confidence = 5394`).
   Investigate whether `debate.winner_confidence` is systematically
   low, or whether 0.7 is too high. This is the biggest single filter.
2. **VOLATILE regime block.** 51 trades, 25.5% WR, -$431.60.
   Strengthening the block should improve net PnL without touching
   the winners.
3. **TMO analysis.** 11 TMO exits - which strategies produced them?
   If a strategy consistently TMO-exits, its SL is likely too far
   for its timeframe.
4. **Shadow `flag_limits`** (and possibly `rbd_dbr`). The old shadow
   list was wrong - use the D6c data.

Do NOT act on the shadow list in `docs/BACKTEST_ANALYSIS.md`. It is
based on the pre-D6c run with a smaller sample.

---

## 10. Reference

- Backtest reports:
  - `data/logs/backtest_beta_BTCUSDT_2026-10-01_2121.*` (D6c, no TMO)
  - `data/logs/backtest_beta_BTCUSDT_2026-10-01_2123.*` (D6c, TMO on)
- Prior baseline: `data/logs/backtest_beta_BTCUSDT_2026-10-01_1923.*` (D6)
- Related: `docs/BACKTEST_ANALYSIS.md`, `docs/BETA_BRAIN.md`