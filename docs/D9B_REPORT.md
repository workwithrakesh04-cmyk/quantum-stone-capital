# Delivery 9b Report - QSC Backtest

**Run date:** 2026-10-02
**Scope:** Build a QSC backtest harness, measure MainBrainV2 on
BTCUSDT 5m, compare with Beta.
**Status:** COMPLETE. **QSC is not tradeable as-implemented.** Three
structural bugs found (one fixed, two open).
**QSC files touched:** none.

---

## 1. Headline

D9b built a QSC backtest harness parallel to BetaBacktester and ran
MainBrainV2 over 5,000 and 20,000 candles of BTCUSDT 5m.

**Result on 20,000 candles:**

    Starting balance:   $10,000.00
    Ending balance:     $-7,110.90      (yes, negative)
    Net PnL:            $-17,110.90  (-171.11%)
    Max drawdown:       $19,571.65   (190.79% - artifact; see below)
    Total trades:       1,302
    Win rate:           57.45%
    Profit factor:      0.805
    Avg win / avg loss: $94.14 / $-158.00
    Expectancy/trade:   $-13.14
    Sharpe:             -5.75
    Sortino:            -6.97
    Calmar:             -0.90

**QSC loses money systematically.** Every active strategy is negative.

| Strategy | Trades | WR% | PnL |
|---|---|---|---|
| trap_double_top | 539 | 54.9% | -$5,531.92 |
| trap_fake_breakout_bearish | 258 | 51.9% | -$6,010.14 |
| ifvg | 504 | 50.8% | -$13,410.57 |

**This is a measurement result, not a failure of D9b.** The
harness works. What it revealed is that QSC is not profitable as
currently implemented.

---

## 2. What D9b delivered

### 2a. `backtest/qsc_context.py`

A real MarketContext builder. QSC's `MainBrainV2.run` expects a
context with pre-computed momentum, rsi, volatility, regime, bos,
and delta. Previously `scripts/run_hybrid.py` fed it fake values
(hardcoded RSI=50, regime derived from a 20-bar momentum sign,
synthetic highs/lows). This module computes them properly:

- momentum (20-bar)
- RSI (14-bar Wilder)
- ATR / volatility
- BOS (swing high/low breaks)
- delta proxy (volume-weighted candle bodies)
- session and killzones from candle timestamps
- regime from Beta's tagger, normalised to QSC's lowercase form

Test count: 31.

### 2b. `backtest/qsc_backtester.py`

The harness. Mirrors `BetaBacktester`:

- Fetches candles via `HistoricalLoader`
- Builds real contexts via `qsc_context.build_market_context`
- Runs `MainBrainV2.run` per candle
- Bridges `PipelineResult` to `PaperTrader` via `_open_qsc_trade`
- Same `enrich()` metrics as Beta
- **Hybrid explicitly disabled** (nulls `brain._beta` and
  `brain._arbiter` after construction; does NOT modify QSC source)

### 2c. `scripts/backtest_qsc.py`

The CLI. Mirrors `scripts/backtest_beta.py`. Output files prefixed
`backtest_qsc_*` so they do not clash with Beta logs.

---

## 3. Bug 1 - SL/TP inversion for shorts (FIXED)

The first 5k run reported **+372% with 91% win rate** - a fake
result. Diagnostic showed:

    SELL with SL below entry (WRONG): 331 / 358

QSC's `PipelineResult` produces direction-agnostic stop/target
levels:
    stop_loss   = min(lows[-10:]) * 0.999
    take_profit = max(highs[-10:]) * 1.001

These are long-oriented. For a short, the stop must be ABOVE entry
and the target BELOW. The bridge was passing them through
unchanged, so every short "stopped out" at a price below entry and
`PaperTrader` recorded it as a **win** - because
`pnl = (entry - exit) * qty` with `exit < entry`.

**Fix:** `_open_qsc_trade` now swaps `sl, tp` for shorts. After the
fix:

    SELL with SL below entry (WRONG): 0

This is a D9b bridge fix. It does NOT touch QSC source.

---

## 4. Bug 2 - `min_rr_ratio: 2.0` is dead config (OPEN)

`config/master.yaml` line 72 declares `min_rr_ratio: 2.0`.
**No code enforces it.**

The `StrategyJuror.judge()` in `jurors/strategy_juror.py` checks:
1. `strategy_name` exists
2. regime match
3. confluence >= `min_confluence_score`
4. `passes_filter` (warning only)
5. `agreeing_frameworks` (warning only)

**There is no RR check anywhere.** The `min_rr_ratio` value is
declared but unused.

Evidence from the 20k run:

    Mean realized RR:  0.894
    RR 0.0-0.5: 935 (71.8%)
    RR 0.5-1.0: 251 (19.3%)
    RR 1.0-1.5:  37 (2.8%)
    RR 1.5-2.0:  20 (1.5%)
    RR 2.0+:     79 (6.1%)

94.0% of opened trades have RR < 2.0. The risk-reward geometry is
inverted: the average SL distance is far larger than the average
TP distance.

**Fixing this requires a QSC source change** (either enforcing
`min_rr_ratio` in the StrategyJuror, or fixing
`_stop_from_context` / `_tp_from_context` to produce balanced
levels). Deferred to a fresh session.

---

## 5. Bug 3 - direction from short-term momentum (OPEN)

`core/main_brain_v2.py::_build_proposal`:

    direction="long" if (context.momentum or 0) >= 0 else "short",

**Direction is chosen by the sign of 20-bar momentum.** In a
trending market, this shorts into uptrends on pullbacks.

The 20k window (2026-07-24 to 2026-10-01) was **bullish** - BTC went
from ~$65k to ~$79k. The active strategies
(`trap_double_top`, `trap_fake_breakout_bearish`, `ifvg`) are all
short-biased patterns. On this window they were short almost the
entire time.

**Fixing this requires a QSC source change** (probably to use a
longer-horizon trend filter, or to weight direction by
strategy-specific bias rather than raw momentum). Deferred to a
fresh session.

---

## 6. The economics that make QSC lose

Even at 57.45% win rate, QSC loses because the loss per trade is
larger than the win:

    0.5745 * $94.14  -  0.4255 * $158.00
    = $54.10 - $67.23
    = -$13.13 per trade

This matches the reported `expectancy_usd: -13.14` exactly.

**Exit distribution (20k):**

    CLOSED_TP:       689 (52.9%)
    CLOSED_TIMEOUT:  454 (34.9%)
    CLOSED_SL:       159 (12.2%)

34.9% of trades hit the 12-bar timeout rather than resolving. The
timeouts average a loss (see sample trades in the CSV), so they
contribute to the negative expectancy even though TP fires more
often than SL.

---

## 7. Comparison with Beta on the same window

| Metric | Beta (D8c-3) | QSC (D9b) |
|---|---|---|
| Net PnL | +8.33% | -171.11% |
| Max DD % | 4.67% | 190.79% (artefact) |
| Trades | 102 | 1,302 |
| Win rate | ~47% | 57.45% |
| Profit factor | 1.36 | 0.805 |
| Sharpe (median) | +1.045 | -5.75 |
| Calmar | 2.31 | -0.90 |

**Beta makes money; QSC loses money.** On the same data, same
timeframe, same paper trader.

This is a real, measured result. It was NOT visible before D9b -
the only prior "evidence" was a 5-candle probe that showed fake
+372% due to the SL/TP inversion.

---

## 8. What D9a would have shown

The planned hybrid demo (D9a) would have run QSC + Beta + Arbiter
against live data, routing sim trades to two demo accounts, and
shown the results in the dashboard.

**With QSC as-implemented, that demo would have shown a losing
system.** The arbiter would mostly return `QSC_ONLY` at 0.5x size
(QSC fires 30x more often than Beta), and those trades would lose
money in sim.

**Decision: D9a is deferred until QSC is fixed.**

The D8 shadow infrastructure already demonstrates Beta's live
behavior (that's what `scripts/shadow_run.py` does). Adding QSC to
a live loop before it's fixed has no value.

---

## 9. What's next

**QSC needs a source-level fix**, not config tuning. The three
bugs:

1. ✅ **SL/TP inversion for shorts** - fixed in D9b's bridge
2. ❌ **`min_rr_ratio: 2.0` is dead** - needs a real RR gate
3. ❌ **Direction from momentum shorts into uptrends** - needs a
   trend-aware direction rule

Each is a small, targeted change to QSC's source. Together they
would materially change what QSC does. But they are QSC source
changes, and the project has committed to not modifying QSC
except for a specific D5b patch.

**Recommended next delivery (D9b-2, fresh session):**

- Implement the `min_rr_ratio` gate in `StrategyJuror` OR
  replace `_stop_from_context` / `_tp_from_context` with
  balanced levels
- Add a trend filter to direction selection
- Re-run the 20k backtest
- Walk-forward validate on the result (D9b-3)

Do NOT do this in the same session as D9b. The findings deserve
fresh eyes, and the fix needs to be designed against a clean
understanding of the three bugs - not patched in reactive mode.

---

## 10. Files added / changed

**Created:**
- `backtest/qsc_context.py`
- `backtest/qsc_backtester.py`
- `scripts/backtest_qsc.py`
- `tests/test_d9b_qsc_context.py` (31 tests)
- `docs/D9B_REPORT.md` (this file)

**Modified:**
- `docs/RESUME_PROMPT.md` - D8b pointer addendum that was
  previously uncommitted
- `docs/STEP_LOG.md` - step 187 entry

**Not changed:**
- All QSC files under `core/`, `jurors/`, `workers/`, `strategies/`
- `config/`
- `beta_brain/`
- `backtest/beta_backtester.py`, `backtest/walk_forward_beta.py`

**Tests:** 666 -> 697 (+31)

---

## 11. Reference

- QSC 20k backtest: `data/logs/backtest_qsc_BTCUSDT_2026-10-02_2321.*`
- QSC 5k backtest (fake, pre-fix): `data/logs/backtest_qsc_BTCUSDT_2026-10-02_2309.*`
- QSC 5k backtest (fixed): `data/logs/backtest_qsc_BTCUSDT_2026-10-02_2318.*`
- Beta baseline for comparison: `data/logs/walk_forward_beta_BTCUSDT_2026-10-02_2209.*`
- Related docs: `docs/D8C3_REPORT.md`, `docs/D8_REPORT.md`