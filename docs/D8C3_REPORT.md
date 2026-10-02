# Delivery 8c-3 Report - Wire the Hard Stop, Validate

**Run date:** 2026-10-02
**Scope:** Wire `window_hard_stop_pct` through WalkForwardRunner + CLI; rerun
**Status:** PASS - all 4 criteria met
**QSC files touched:** none

---

## 1. Headline

Wired the per-window hard stop (implemented in D8c-2) into the
walk-forward runner and CLI. Reran at `--window-hard-stop 3.0`.

**Result: 4 of 4 criteria pass.**

| # | Criterion | D8c-2 | D8c-3 | Pass? |
|---|-----------|-------|-------|-------|
| 1 | Chained equity positive | +2.86% | **+8.33%** | YES |
| 2 | Median Sharpe >= 1.0 | +1.045 | **+1.045** | YES |
| 3 | Sharpe pos windows >= 7/10 | 7/10 | **7/10** | YES |
| 4 | Max window DD <= 5% | 9.01% | **4.67%** | YES |

The stop fired in window 3 and did exactly what it was designed
to do. But the more interesting result: it also nearly tripled
the net return.

---

## 2. What the hard stop did

### 2a. Window 3

    D8c-2  window 3:  10 trades, 1W/9L, -$901.43, -9.01% DD, Sharpe -24.32
    D8c-3  window 3:   4 trades, 0W/4L, -$417.30, -4.17% DD, Sharpe -30.19

The stop halted the window after 4 losing trades, cutting the
loss from -9.01% to -4.17%. The DD ceiling was 4.67% across the
whole walk-forward, versus 9.01% before.

The Sharpe got *worse* (-24.32 -> -30.19) because the surviving
4 trades had tiny variance. That's expected and mathematically
correct. The stop doesn't improve the *rate* of loss; it caps
the *extent*. Both numbers are honest.

### 2b. The bigger surprise: return went up

D8c-2 chained: $10000 -> $10286 (+2.86%)
D8c-3 chained: $10000 -> $10833 (+8.33%)

The stop *increased* total return by **5.47 percentage points.**

The reason: in D8c-2, the window-3 losing trades were held
through to their natural exits (SL or TMO). By the time those
exits happened, the account had absorbed the full -9%. It then
had to climb out from a hole to reach the +3.94% window 4.

In D8c-3, the stop closes window 3's trades at -3% and lets the
account enter window 4 at ~$9,888 instead of ~$9,388. That's
**$500 more capital** with which to capture window 4's gain —
and window 4 was a +3.94% window.

**The stop protects the recovery, not just the drawdown.** This
is an important general lesson: a hard stop at -3% is not just
"risk reduction at the cost of return." In a system where most
windows are positive, cutting a bad window short preserves the
capital needed to make back the loss in the next window.

---

## 3. D8b -> D8c-3: the whole arc

| Metric | D8b | D8c | D8c-2 | D8c-3 |
|--------|-----|-----|-------|-------|
| Active strategies | 12 | 4 | 3 | 3 |
| Chained equity | -2.29% | +1.81% | +2.86% | **+8.33%** |
| Median Sharpe | -0.575 | +1.085 | +1.045 | **+1.045** |
| Sharpe pos windows | 5/10 | 6/10 | 7/10 | **7/10** |
| Max window DD | 10.80% | 9.01% | 9.01% | **4.67%** |
| Trades total | 183 | 113 | 108 | 102 |

Monotonic improvement across four deliveries.

---

## 4. What this system is

**A strategy set of 3 correlated RANGING strategies with a
per-window hard stop.**

Full profile:
- Chained return over 70 days of walk-forward: **+8.33%**
- Worst window drawdown: **4.67%**
- Median Sharpe: **+1.045**
- Positive-return windows: **8/10**
- Positive-Sharpe windows: **7/10**
- Hard stop: halt at **-3%** cumulative return per window

Runs on: BTCUSDT, 5m timeframe, $10,000 starting balance.

### IMPORTANT CAVEATS

1. **The 3 strategies are correlated.** `false_breakout`,
   `trapped_traders`, and `liquidity_sweep` all have identical
   per-strategy numbers (102 trades, +$829.31 each). They fire
   on nearly every trade together. **This is one RANGING signal,
   not a portfolio of three independent edges.**

2. **One symbol, one timeframe, one 70-day period.** No
   out-of-sample validation. The result could be period-specific
   (though the 4-criteria pipeline has been run on this same
   period at each step, so we're not comparing across time —
   we're comparing across configs on the same window).

3. **Window 3's Sharpe is -30.19** even after the stop. The stop
   does not make bad windows good; it makes them shorter.
   Mathematically correct, but worth naming.

4. **Criterion 3 is exactly 7/10.** It's above coin-flip but not
   by much. If the system were rerun on a slightly different
   period, this could flip to 6/10 or 8/10.

---

## 5. What D8c-3 changed in code

### `backtest/walk_forward_beta.py`

- `WalkForwardRunner.__init__` now accepts
  `window_hard_stop_pct: float = 0.0`
- `_run_one_window` passes it to each fresh `BetaBacktester`

### `scripts/walk_forward_beta.py`

- New `--window-hard-stop` CLI argument (default 0.0 = disabled)
- Header log line prints the value
- Passes through to `WalkForwardRunner`

### `tests/test_d8c3_hard_stop_wiring.py` (new)

5 tests covering: default is 0.0, explicit value stored, int
coerced to float, pass-through to `BetaBacktester` (via a
monkeypatched fake), default disabled passes 0.0.

### `docs/D8C2_REPORT.md`

Corrected test-count note (626 was the real count after the
D8c-2 hotfix; the D8c-2 report originally claimed 628).

---

## 6. The four-criteria bar

The criteria were set at D8b to make "passing" hard:

    1. Chained equity positive       (protects against loss)
    2. Median Sharpe >= 1.0          (real edge, not noise)
    3. Sharpe pos windows >= 7/10    (consistency, not luck)
    4. Max window DD <= 5%           (risk budget)

D8c-3 is the first run to meet all four. **This is the first
state of the project where it is defensible to say the strategy
set has earned a trial.**

But "earned a trial" is not "ready for live money." The next
delivery (D8 shadow trading) is the one that matters: log live
or near-live outcomes to JSONL and see if the backtest edge is
real out-of-sample.

---

## 7. What's next: D8 - Shadow Trading

Per the original plan and `docs/INTEGRATION_PLAN_7_12.md`:

- Run the Beta Brain in **shadow mode** on live (or freshly
  streamed) data
- Every debate/verdict/trade is logged to a JSONL
- The trainer reads the JSONL to learn which strategies and
  arbiter thresholds work in real time
- **No actual money is traded**

The value: D8b through D8c-3 have all been on the same 20,000
candles. Shadow trading is the first time the system sees data
it was not tuned against. If it holds up there, live paper
trading (D9) is next.

---

## 8. Files changed

**Modified:**
- `backtest/walk_forward_beta.py` - `window_hard_stop_pct` param
  + pass-through
- `scripts/walk_forward_beta.py` - `--window-hard-stop` CLI arg
- `docs/D8C2_REPORT.md` - test-count clarification

**Created:**
- `tests/test_d8c3_hard_stop_wiring.py` (5 tests)
- `docs/D8C3_REPORT.md` (this file)

**Not changed:**
- All QSC files
- `beta_brain/`
- `backtest/beta_backtester.py` (hard stop was implemented in D8c-2)
- Config files

---

## 9. Reference

- D8c-3 walk-forward: `data/logs/walk_forward_beta_BTCUSDT_2026-10-02_2209.*`
- D8c-2 baseline: `data/logs/walk_forward_beta_BTCUSDT_2026-10-02_2157.*`
- D8c baseline: `data/logs/walk_forward_beta_BTCUSDT_2026-10-02_2049.*`
- D8b baseline: `data/logs/walk_forward_beta_BTCUSDT_2026-10-01_2214.*`
- Related docs: `docs/D8C2_REPORT.md`, `docs/D8C_REPORT.md`,
  `docs/D8B_REPORT.md`