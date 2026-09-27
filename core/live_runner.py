"""
Live Runner: the loop that connects a broker to the Main Brain.
Works with any BaseBroker — paper or MT5.
"""
import time
from dataclasses import dataclass
from typing import Callable, List, Optional

from brokers.base_broker import BaseBroker
from core.market_context import MarketContext
from core.main_brain_v2 import MainBrainV2


@dataclass
class RunnerConfig:
    symbols: List[str]
    timeframe: str = "5m"
    poll_seconds: float = 5.0
    account_name: str = "personal"
    dry_run: bool = True    # never actually place orders if True


class LiveRunner:
    def __init__(
        self,
        broker: BaseBroker,
        brain: Optional[MainBrainV2] = None,
        config: Optional[RunnerConfig] = None,
        context_builder: Optional[Callable[[BaseBroker, str, str], MarketContext]] = None,
    ):
        self.broker = broker
        self.brain = brain or MainBrainV2()
        self.config = config or RunnerConfig(symbols=["BTCUSD"])
        self.context_builder = context_builder or self._default_context
        self._stop = False

    def _default_context(self, broker: BaseBroker, symbol: str, timeframe: str) -> MarketContext:
        """Minimal context: just price. Real feeds should provide more."""
        price = broker.last_price(symbol)
        return MarketContext(
            symbol=symbol,
            timeframe=timeframe,
            closes=[price] if price else [],
            highs=[price] if price else [],
            lows=[price] if price else [],
            opens=[price] if price else [],
            volumes=[0.0],
        )

    def stop(self) -> None:
        self._stop = True

    def tick_once(self) -> List[dict]:
        """Run one pass over all symbols. Return decisions."""
        results = []
        for symbol in self.config.symbols:
            try:
                ctx = self.context_builder(self.broker, symbol, self.config.timeframe)
                decision = self.brain.run(ctx, account_name=self.config.account_name)
                results.append({
                    "symbol": symbol,
                    "decision": decision.decision,
                    "direction": decision.direction,
                    "confidence": decision.confidence,
                    "strategy": decision.strategy_name,
                    "reasons": decision.reasons,
                })
                # If a trade is approved and not dry-run, place it
                if decision.is_trade and not self.config.dry_run:
                    self._place_order(decision, symbol)
            except Exception as e:
                results.append({"symbol": symbol, "error": str(e)})
        return results

    def _place_order(self, decision, symbol: str) -> Optional[object]:
        side = "buy" if decision.direction == "long" else "sell"
        volume = decision.position_size or 0.0
        if volume <= 0:
            return None
        return self.broker.open_order(
            symbol=symbol,
            side=side,
            volume=volume,
            stop_loss=decision.stop_loss,
            take_profit=decision.take_profit,
            order_type=decision.order_type,
        )

    def run_forever(self, max_iterations: Optional[int] = None) -> None:
        it = 0
        while not self._stop:
            self.tick_once()
            it += 1
            if max_iterations is not None and it >= max_iterations:
                break
            time.sleep(self.config.poll_seconds)
