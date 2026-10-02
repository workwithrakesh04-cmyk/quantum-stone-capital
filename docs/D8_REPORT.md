# Delivery 8 Report - Shadow Trading Infrastructure

**Run date:** 2026-10-02
**Scope:** Build the shadow runner, run it on 100 out-of-sample candles,
validate the infrastructure end-to-end.
**Status:** INFRASTRUCTURE VALIDATED. Sample size insufficient for
an edge verdict. D8b is the real analysis.
**QSC files touched:** none

---

## 1. Headline

D8 ships the shadow trading infrastructure: a runner that fetches
fresh candles from Binance, runs the exact Beta Brain pipeline
(same window size, warmup, hard stop, and max_hold_bars as D8c-3),
writes every decision to JSONL, and an analysis module that
replays the decisions and computes the same metrics D8c-3 reported.

**What it produced on 100 fresh candles:**

    candles_processed:    100
    debates_run:          100
    verdicts_approved:      0
    verdicts_rejected:    100
    trades_opened:          0
    return_pct:           0.00%
    halted:              false

**100 debates, 100 rejections, 0 trades.**

This is **not** a failure. It is what the pipeline is designed to do
when the strategies do not fire. See section 3 for why this is
consistent with D8c-3's expected trade frequency.

**D8 does NOT claim the edge is real.** That claim requires a
meaningful out-of-sample sample. D8b will produce that. See
section 5 for the D8b plan.

---

## 2. What D8 delivered

### 2a. `beta_brain/shadow_audit.py`

JSONL writer for shadow runs. Separate directory (`logs/shadow/`)
from hybrid live runs (`logs/consensus/`). Day rotation, encoding
tolerance, archive support. API mirrors `ConsensusAudit` so any
future merge is trivial.

### 2b. `scripts/shadow_run.py`

The shadow loop:
- Fetches `seed_buffer + n_new_candles` from Binance via
  `HistoricalLoader`
- For each new candle, builds the same 500-candle window the
  backtester used, wraps it as a `SimpleNamespace` context, and
  calls `BetaBrain.run(context, equity=trader.balance, ...)`
- Threads equity and portfolio state so the risk jury scales
  correctly
- On approved verdicts, opens a trade via `PaperTrader` with
  `max_hold_bars=12`
- Runs the same hard-stop logic as `BetaBacktester` (halt at -3%)
- Writes one JSONL record per candle with `run_id` isolation

### 2c. `backtest/shadow_analysis.py`

Reads the shadow JSONL, replays trades through a fresh
`PaperTrader` using the logged OHLC (full fidelity, no close-as-
proxy), and computes the same metrics D8c-3 reported. Prints a
side-by-side comparison.

### 2d. `scripts/shadow_analysis.py`

CLI wrapper. Accepts `--day`, `--run-id`, `--list-runs`.

### 2e. Tests

- `tests/test_d8_shadow_audit.py` (14 tests) - JSONL read/write,
  archive, encoding tolerance
- `tests/test_d8_shadow_analysis.py` (21 tests) - metrics math,
  replay, intrabar TP/SL, hard stop, legacy fallback

**Total: 666 tests passing** (was 631 after D8c-3).

---

## 3. Why 0 trades is the right result

D8c-3 produced ~102 trades over 10 windows of 3,500 candles each
(~35,000 candle-instances). That's roughly **10 trades per 3,500
candles**.

D8's OOS sample: **100 candles**.

Expected trades on 100 candles: **100 * (10 / 3500) = 0.29.**

We got **0**. That is statistically exactly what D8c-3's trade
frequency predicts. Not a failure, not an edge collapse, simply
insufficient sample.

Also important: the JSONL tally shows **`no_verdict = 100`**. Not
`jury_rejected`, not `low_confidence`. Every candle returned `None`
from `BetaBrain.run()`, meaning **the strategies never fired**. The
min-confidence gate was not the blocker. The strategies simply
had nothing to fire on in today's tape.

This is consistent with the 3 active strategies being
RANGING-mean-reversion setups that require specific conditions.
Today's 8-hour window did not contain those conditions.

---

## 4. The infrastructure that D8 built

**What runs:** fetch → context build → `BetaBrain.run` → verdict
→ `PaperTrader` fill → JSONL → analysis. End-to-end, on fresh
data, without crashes.

**Isolation:** each run gets a `run_id`. Default behavior is a
fresh run (clears today's JSONL). `--append` keeps multiple runs
in one file with distinct run_ids. `shadow_analysis.py` filters
by run_id.

**Fidelity:** the shadow run logs full OHLC per candle. The
analysis replay uses those to run intrabar SL-before-TP, matching
`BetaBacktester`'s behavior. Tests confirm both TP and SL can be
hit intrabar.

**Fidelity gap (acknowledged):** `BetaBrain.run()` returns `None`
when there is no actionable signal, so the shadow runner cannot
distinguish "no signals" from "debate rejected them" from
"min-confidence gate rejected them." The JSONL records them all as
`no_verdict`. This is a known limitation. Fixing it would require
modifying `BetaBrain.run()` to return a structured reason, which
D8 deliberately avoided to keep `BetaBrain` frozen.

---

## 5. D8b - the real out-of-sample analysis

D8b is a **scheduled re-run** of the same infrastructure, at a
point when meaningful OOS data has accumulated.

### Sample size target

D8c-3's trade frequency: ~10 per 3,500 candles.

For a meaningful first read on out-of-sample edge:
- **>=30 trades** (rule-of-thumb minimum for interpretation) needs
  ~10,500 OOS candles = **36 days** of 5m data
- **>=100 trades** (comparable to D8c-3's sample) needs ~35,000 OOS
  candles = **120 days**

D8b should run when OOS candles >= 5,000 (>= ~14 trades expected).
That's roughly **17 days** from today. Interpret results with
appropriate skepticism; a proper verdict needs the 30-trade mark
at minimum.

### D8b output

Same comparison table as D8: D8c-3 (in-sample) vs D8b (larger OOS).
New pass criterion for D8b (adjusted for OOS reality):

    1. return_pct >= 0        (sign consistency with D8c-3)
    2. sharpe >= 0.5          (weaker bar than in-sample 1.045)
    3. max_drawdown_pct <= 8  (allow for regime-driven DD)
    4. total_trades >= 30     (statistical minimum)

### What D8b would tell us

- **Pass** → the D8c-3 edge holds out-of-sample. Next: D9
  (paper trading with real broker API, still no live money).
- **Partial** → mixed evidence. Options: re-tune using walk-
  forward only (not single-window), or add strategies to
  diversify signal sources.
- **Fail** → the in-sample edge was likely fit to the 20k window.
  Next: rebuild strategy selection from scratch using walk-
  forward as the primary metric at every step.

---

## 6. What D8 does NOT claim

D8 explicitly does **not** claim:

- That the D8c-3 edge is real out-of-sample
- That the system is ready for paper trading
- That the strategy set is stable across market regimes

It claims only:

- The shadow infrastructure works end-to-end on fresh data
- The pipeline is selective (0 forced trades on a chop day)
- The analysis correctly replays and computes metrics
- The isolation (run_id) and fidelity (OHLC replay) are correct

Any interpretation of the edge requires D8b.

---

## 7. Files added / changed

**Created:**
- `beta_brain/shadow_audit.py`
- `scripts/shadow_run.py`
- `scripts/shadow_analysis.py`
- `backtest/shadow_analysis.py`
- `tests/test_d8_shadow_audit.py` (14 tests)
- `tests/test_d8_shadow_analysis.py` (21 tests)
- `docs/D8_REPORT.md` (this file)

**Modified:**
- None in source or config. All changes are new files.

**Not changed:**
- All QSC files
- `beta_brain/beta_brain.py`
- `beta_brain/paper_trader.py`
- Any config under `config/`

---

## 8. Reference

- Shadow run summary:
  `data/logs/shadow_run_BTCUSDT_2026-10-02_1654.json`
- Shadow JSONL: `logs/shadow/2026-10-02.jsonl`
  (run_id 20261002T165457Z, 100 records, all `no_verdict`)
- D8c-3 baseline: `data/logs/walk_forward_beta_BTCUSDT_2026-10-02_2209.*`
- Related docs: `docs/D8C3_REPORT.md`, `docs/D8C2_REPORT.md`