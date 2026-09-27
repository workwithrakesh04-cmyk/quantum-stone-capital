# Quantum Stone Capital — Knowledge Base

## Master Resource Registry (75+ Resources)

### Classical Technical Analysis
- Wyckoff Volumes 1-9, Anatomy, Schematics
- Murphy — El Inversor Visual
- Encyclopedia of Candlestick Charts (103 patterns)
- CMT Level II 2024

### Smart Money / ICT
- Fede Esses — Entry Types, Liquidity, Market Makers, SC, IC
- CRT Secrets Series (TradesbyVee)
- David Woods — Advanced ICT Institutional SMC
- Deivid FX — LIT & TRAP Trading

### Volume / Order Flow
- Anna Coulling — VPA, Three Dimensional Approach
- Buff Pelz Dormeier — Investing with Volume Analysis
- Footprint Guide (El Trader de Huella)
- Shaleen — Volume and Open Interest

### Market Profile
- James Dalton — Markets in Profile
- Curso MP y VP 2.0 (enbolsa.net)

### Market Microstructure
- Brunnermeier — Market Making Theory
- Kyle (1985) — Strategic Informed Trading
- Glosten-Milgrom (1985)

### Institutional / Derivatives
- FRM Part 1 Book 3 (Hull/GARP)
- CFA Level I Vols 1, 3, 4

### Quantitative Finance
- Ernest Chan — Quantitative Trading
- Bell — Quantitative Finance For Dummies
- Paul Johnson — Mathematical Models in Finance
- Sheldon Ross — A First Course in Probability
- Larry Wasserman — All of Statistics

### Machine Learning / AI
- Stefan Jansen — Hands-On ML for Algorithmic Trading
- Muller & Guido — Introduction to ML with Python
- Andrew Ng — Machine Learning Yearning
- Dey et al. — ML-Based Automated Trading (Indian Market)
- Glucksman & Lahanis — Online Quantitative Trading Strategies

### Neural Networks / MQL5
- Laurent Fausett — Fundamentals of Neural Networks
- Stanislav Korotky — MQL5 Programming for Traders

### Turtle / Systematic
- Curtis Faith — Way of the Turtle
- Tomas Nesnidal — Breakout Trading Revolution
- Rundo et al. — GTSbot (HFT Grid Trading)

### Day / Swing Trading
- Andrew Aziz — Advanced Techniques in Day Trading
- Andrew Aziz — How to Day Trade for a Living
- Brian Pezim — How to Swing Trade
- Justin Kuepper — Day Trading
- Timothy Knight — High-Probability Trade Setups

### Harmonic / Patterns
- Young Ho Seo — Guide to Precision Harmonic Pattern Trading

### Psychology
- Brett Steenbarger — El entrenador de trading
- David Trullas — Bienvenidos al mundo real de la bolsa
- Maxwell Maltz — Psycho-Cybernetics
- Mark Douglas — Trading in the Zone

### Forex / Intermarket
- Anna Coulling — Three Dimensional Approach
- Deivid FX — LIT & TRAP Trading

### Foundations
- CMP332 — Quantitative Aptitude
- Goodwin — Trading Secrets of the Inner Circle
- Frost & Prechter — Elliott Wave Principle

## Core Formulas

### Market Microstructure
    Kyle lambda:      lambda = 0.5 * sqrt(Sigma0 / sigma_u^2)
    Bayesian update:  a = E[v | buy order]

### Pricing (FRM)
    Forward price:      F = S * (1+R)^T
    Put-call parity:    c + PV(K) = p + S
    Convenience yield:  F = S * e^((R + U - Y) * T)

### Risk (FRM + Turtle)
    Optimal hedge ratio: h* = rho * (sigma_S / sigma_F)
    2N stop (Turtle):    2 * ATR(20)
    R-Cubed:             RAR% / (Avg Max DD * Duration Adjustment)

### Probability (Ross + Wasserman)
    Bayes:              P(H|E) = P(E|H)P(H) / P(E)
    Conditional var:    Var(X) = E[Var(X|Y)] + Var(E[X|Y])
    Chebyshev:          P(|X-mu| >= k*sigma) <= 1/k^2
    Bootstrap CI:       percentile method, B=1000

### Elliott Wave
    Wave 3 vs Wave 1:   1.618 or 2.618
    Wave 4 subdivision: 0.382 / 0.618
    Zigzag:             Wave C = Wave A (or 1.618/0.618)

## The 7-Layer Architecture

See docs/ARCHITECTURE.md for the full specification.
