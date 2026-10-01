"""Agreement metrics."""
from typing import Optional


def normalize_direction(d):
    if d is None:
        return "HOLD"
    d = str(d).upper()
    if d in ("BUY", "LONG"):
        return "LONG"
    if d in ("SELL", "SHORT"):
        return "SHORT"
    return "HOLD"


def agreement_label(qsc_dir, beta_dir):
    q = normalize_direction(qsc_dir)
    b = normalize_direction(beta_dir)
    if q == "HOLD" and b == "HOLD":
        return "BOTH_HOLD"
    if q == b:
        return "BOTH_AGREE"
    if q == "HOLD":
        return "BETA_ONLY"
    if b == "HOLD":
        return "QSC_ONLY"
    return "DISAGREE"


def confidence_weight(qsc_conf, beta_conf):
    try:
        return round((float(qsc_conf) + float(beta_conf)) / 2.0, 3)
    except (TypeError, ValueError):
        return 0.0
