"""Strategy Analyzer - ported from HFT_Brain.

Tracks per-strategy performance. Attributes a trade's PnL proportionally
to the strategies that fired same-direction.
"""
from typing import List, Dict, Any
from collections import defaultdict


class StrategyAnalyzer:
    def __init__(self):
        self.records: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {"wins": 0, "losses": 0, "pnl": 0.0, "trades": 0}
        )
        self.regime_records: Dict[str, Dict[str, Dict[str, Any]]] = defaultdict(
            lambda: defaultdict(lambda: {"wins": 0, "losses": 0, "pnl": 0.0, "trades": 0})
        )
        self.direction_records: Dict[str, Dict[str, Dict[str, Any]]] = defaultdict(
            lambda: defaultdict(lambda: {"wins": 0, "losses": 0, "pnl": 0.0, "trades": 0})
        )

    def record_trade(
        self,
        contributing_strategies: List[str],
        direction: str,
        pnl_usd: float,
        regime: str,
    ) -> None:
        if not contributing_strategies:
            return
        is_win = pnl_usd > 0
        n = len(contributing_strategies)
        pnl_per_strat = pnl_usd / n

        for strat in contributing_strategies:
            rec = self.records[strat]
            rec["trades"] += 1
            rec["pnl"] += pnl_per_strat
            if is_win: rec["wins"] += 1
            else: rec["losses"] += 1

            rrec = self.regime_records[regime][strat]
            rrec["trades"] += 1
            rrec["pnl"] += pnl_per_strat
            if is_win: rrec["wins"] += 1
            else: rrec["losses"] += 1

            drec = self.direction_records[direction][strat]
            drec["trades"] += 1
            drec["pnl"] += pnl_per_strat
            if is_win: drec["wins"] += 1
            else: drec["losses"] += 1

    def to_dict(self) -> Dict[str, Any]:
        out = {"strategies": {}, "regimes": {}, "directions": {}}
        for name, rec in self.records.items():
            trades = rec["trades"]
            out["strategies"][name] = {
                "trades": trades,
                "wins": rec["wins"], "losses": rec["losses"],
                "win_rate": round(rec["wins"] / trades * 100, 2) if trades > 0 else 0,
                "net_pnl": round(rec["pnl"], 2),
                "avg_pnl_per_trade": round(rec["pnl"] / trades, 2) if trades > 0 else 0,
            }
        for regime, strats in self.regime_records.items():
            out["regimes"][regime] = {}
            for sname, srec in strats.items():
                trades = srec["trades"]
                out["regimes"][regime][sname] = {
                    "trades": trades,
                    "wins": srec["wins"], "losses": srec["losses"],
                    "win_rate": round(srec["wins"] / trades * 100, 2) if trades > 0 else 0,
                    "net_pnl": round(srec["pnl"], 2),
                }
        for direction, strats in self.direction_records.items():
            out["directions"][direction] = {}
            for sname, srec in strats.items():
                trades = srec["trades"]
                out["directions"][direction][sname] = {
                    "trades": trades,
                    "wins": srec["wins"], "losses": srec["losses"],
                    "win_rate": round(srec["wins"] / trades * 100, 2) if trades > 0 else 0,
                    "net_pnl": round(srec["pnl"], 2),
                }
        return out
