# New Resources - Book Summaries

**Source:** User-provided summary, 2026-10-01
**Purpose:** Conceptual foundation for Deliveries 7-12

Two books summarized:

1. **Volume Profile, Market Profile, Order Flow** (Forthmann)
2. **Follow the Money (FTM Strategy)** - Smart Money Concepts

---

## Book 1 - Volume Profile, Market Profile, Order Flow

### Market Profile (MP) vs Volume Profile (VP)

- **MP (TPO):** time spent at each price. Long time = acceptance. Short time (single print/tail) = rejection.
- **VP:** volume traded at each price. Highest = POC (point of control). 70% range = Value Area.
- **HVN:** high-volume nodes = magnets / support-resistance.
- **LVN:** low-volume nodes = rapid movement zones / targets.
- **Naked POC:** POC from prior session not revisited = magnet.

### Order Flow & Delta

- **Footprints:** buy/sell market orders per price within a candle.
- **Stacked imbalances:** consecutive 2x+ imbalances = aggressive participation.
- **Delta:** net aggressive buy - aggressive sell.
- **Absorption:** heavy sell orders absorbed by passive buyers, price fails to drop.
  This is a reversal / trap signal.

### Manipulation Patterns

- **Stop runs / hunts:** pushing through a level to trigger retail stops.
- **False breakouts:** breakout that immediately reverses.
- **Top/Bottom squeeze:** extreme stop hunt at range extremes, violent reversal.

### Reversal / Trend Setups

- **Change of POC:** POC shifts during session = sentiment shift.
- **Hooks and ledgings:** pause after strong move, breakout = continuation.
- **Broadening tops:** rare; increasing volatility at bull market end.

### Integration Targets

- Feature engineering in beta_brain: poc_distance, va_position, imbalance_score,
  delta_divergence_flag, squeeze_detected_flag.
- New strategies: absorption, stacked imbalances, naked POC reversion, false breakout fade.
- Arbiter weighting based on pattern presence.

---

## Book 2 - Follow the Money (SMC)

### Market Structure

- **BOS (Break of Structure):** trend continuation signal. HH in uptrend, LL in downtrend.
- **CHoCH (Change of Character):** first reversal sign. LH after uptrend / HL after downtrend.
- **Rule:** trade with HTF structure, enter on LTF.

### Liquidity

- **EQH (Equal Highs):** double top = buy-side liquidity.
- **EQL (Equal Lows):** double bottom = sell-side liquidity.
- **Liquidity sweeps/grabs:** price moves to EQH/EQL then reverses. Core trap.

### Order Blocks & Imbalances

- **Order Block (OB):** last opposite candle before an impulsive structure-breaking move.
- **Imbalance (IMB):** price area with severe buy/sell inequality (gap).
- **OBIM:** OB that also contains imbalance. Highest probability setup.
- **Decision Point (DP):** where institutional orders await mitigation.

### FTM Entry Model

1. Analyze HTF (W1, D1, H4) structure.
2. Identify key DP (OBIM) on HTF = Price Reversal Zone.
3. Move to LTF (M15, M5, M1).
4. Wait for price to enter HTF DP.
5. Trigger: LTF Stop Hunt Candle (SHC) within the zone, then mitigated by strong move
   in trade direction. Look for LTF BOS.
6. Enter; SL just beyond SHC (often <5 pips). Tight stop, high R:R.

### Wyckoff Correspondence

- Spring = liquidity grab below trading range
- Test = successful re-test
- SOS (Sign of Strength) = the BOS that confirms new trend

### Integration Targets

- New module: smc_analyzer.py (per-symbol, per-TF SMC features).
- Features for beta_brain: htf_trend, ltf_bos_flag, eqh_eql_proximity,
  obim_zone_proximity, shc_detected_flag.
- Master strategy: HTF bias + OBIM + SHC + LTF BOS -> BUY with tight SL.
- Trainer learns optimal conditions for OBIM success.
