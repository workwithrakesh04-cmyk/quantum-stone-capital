"""Risk Jury - position sizing with adaptive loss scaling.

Uses Beta's own AccountGuard for consecutive-loss state.
"""
from typing import List, Dict, Any
from loguru import logger

from beta_brain.debate.transcript import DebateTranscript
from beta_brain.jury.transcript import RiskVerdict
from beta_brain.account_guard import get_account_guard


class RiskJury:
    def __init__(self, config: dict):
        self.cfg = config
        self.account = config["account"]
        self.risk_cfg = config["risk"]
        self.modes = config["modes"]
        self.sl_cfg = config["stop_loss"]
        self.account_type = self.account.get("account_type", self.account.get("type", "personal"))
        self.loss_scaling = config.get("loss_scaling", {})

    def _scale_factor_from_losses(self, consecutive_losses: int) -> float:
        if not self.loss_scaling.get("enabled", False):
            return 1.0
        thresholds = self.loss_scaling.get("thresholds", {})
        applicable = None
        for th in sorted(thresholds.keys(), reverse=True):
            try:
                th_int = int(th)
            except (ValueError, TypeError):
                continue
            if consecutive_losses >= th_int:
                applicable = thresholds[th]
                break
        return float(applicable) if applicable is not None else 1.0

    def evaluate(
        self,
        debate: DebateTranscript,
        candles: List[dict],
        equity: float,
        mode: str = "scalp",
    ) -> RiskVerdict:
        if debate.winner not in ("BUY", "SELL"):
            return RiskVerdict(
                approved=False, mode=mode,
                reject_reason=f"debate winner is {debate.winner}",
            )

        mode_cfg = self.modes.get(mode)
        if not mode_cfg or not mode_cfg.get("enabled"):
            return RiskVerdict(
                approved=False, mode=mode,
                reject_reason=f"mode {mode} disabled",
            )

        if not candles:
            return RiskVerdict(
                approved=False, mode=mode,
                reject_reason="no candles",
            )

        guard = get_account_guard(self.cfg)
        consecutive = guard.state.consecutive_losses
        scale = self._scale_factor_from_losses(consecutive)

        if scale <= 0.0:
            return RiskVerdict(
                approved=False, mode=mode,
                reject_reason=f"loss scaling blocked ({consecutive} losses)",
            )

        curr_price = candles[-1]["close"]
        direction = debate.winner

        sl_price = self._calc_stop_loss(candles, curr_price, direction)
        sl_dist = abs(curr_price - sl_price)
        if sl_dist <= 0:
            return RiskVerdict(approved=False, mode=mode, reject_reason="SL dist 0")

        min_rr = mode_cfg["min_rr"]
        tp_dist = sl_dist * min_rr
        tp_price = curr_price + tp_dist if direction == "BUY" else curr_price - tp_dist

        risk_pct = mode_cfg.get("risk_per_trade_pct", self.risk_cfg["per_trade_pct"])
        effective_risk_pct = risk_pct * scale
        risk_amount = equity * (effective_risk_pct / 100.0)

        max_sl_dist = curr_price * (self.sl_cfg["max_pct"] / 100.0)
        notes = []
        if scale < 1.0:
            notes.append(f"loss_scale={scale:.2f} ({consecutive} losses)")

        if sl_dist > max_sl_dist:
            notes.append("SL capped")
            sl_dist = max_sl_dist
            if direction == "BUY":
                sl_price = curr_price - sl_dist
                tp_price = curr_price + sl_dist * min_rr
            else:
                sl_price = curr_price + sl_dist
                tp_price = curr_price - sl_dist * min_rr

        qty = risk_amount / sl_dist
        position_size_usd = qty * curr_price

        max_lev = mode_cfg.get("max_notional_leverage", 10.0)
        max_notional = equity * max_lev
        if position_size_usd > max_notional:
            capped_qty = max_notional / curr_price
            notes.append(f"notional cap {max_lev}x")
            qty = capped_qty
            position_size_usd = qty * curr_price
            risk_amount = qty * sl_dist

        logger.info(
            f"BetaRiskJury[{self.account_type}/{mode}]: {direction} "
            f"scale={scale:.2f} qty={qty:.6f} risk=${risk_amount:.2f}"
        )

        return RiskVerdict(
            approved=True, mode=mode,
            position_size_usd=round(position_size_usd, 2),
            position_size_qty=round(qty, 6),
            stop_loss_price=round(sl_price, 2),
            take_profit_price=round(tp_price, 2),
            risk_reward_ratio=min_rr,
            risk_amount_usd=round(risk_amount, 2),
            notes=notes,
        )

    def _calc_stop_loss(self, candles: List[dict], curr_price: float, direction: str) -> float:
        if len(candles) < 14:
            pct = self.sl_cfg["percent_fallback"] / 100.0
            return curr_price * (1 - pct) if direction == "BUY" else curr_price * (1 + pct)

        trs = []
        for i in range(1, 15):
            h = candles[-i]["high"]
            l = candles[-i]["low"]
            if i + 1 <= len(candles):
                pc = candles[-i - 1]["close"]
            else:
                pc = candles[-i]["close"]
            tr = max(h - l, abs(h - pc), abs(l - pc))
            trs.append(tr)

        atr = sum(trs) / len(trs)
        sl_dist = atr * self.sl_cfg["atr_multiplier"]
        return curr_price - sl_dist if direction == "BUY" else curr_price + sl_dist
