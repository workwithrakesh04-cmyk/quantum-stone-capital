"""
Execution Engine.
Handles order splitting, slippage modeling, and Kyle-lambda-aware
order routing. Used by the Execution Juror and Algo Trader.
"""
import math
from typing import List, Optional
from core.order import Order, OrderType, OrderSide, OrderStatus


class ExecutionEngine:
    """
    Minimal simulation-grade execution engine.
    - Calculates slippage using a linear impact model.
    - Splits large orders into TWAP-style child orders.
    - Tracks commission and market impact.
    """

    def __init__(
        self,
        slippage_model: str = "linear",
        max_slippage_pct: float = 0.001,
        commission_per_unit: float = 0.0,
    ):
        self.slippage_model = slippage_model
        self.max_slippage_pct = max_slippage_pct
        self.commission_per_unit = commission_per_unit

    # ---------- slippage ----------

    def compute_slippage(
        self,
        mid_price: float,
        order_size: float,
        avg_volume: float,
        volatility: float,
    ) -> float:
        """
        Return slippage as a fraction of mid_price.
        Linear model: slippage = k * (order_size / avg_volume) * volatility
        Capped at max_slippage_pct.
        """
        if avg_volume <= 0:
            return self.max_slippage_pct
        participation = order_size / avg_volume
        raw = 0.1 * participation * volatility
        return min(raw, self.max_slippage_pct)

    # ---------- order splitting ----------

    def split_order(
        self,
        total_size: float,
        avg_volume: float,
        max_participation: float = 0.001,
    ) -> List[float]:
        """
        Split a large order into child sizes so each child is at most
        max_participation * avg_volume.
        """
        if avg_volume <= 0 or total_size <= 0:
            return [total_size]
        max_child = max_participation * avg_volume
        if total_size <= max_child:
            return [total_size]
        n_children = math.ceil(total_size / max_child)
        child_size = total_size / n_children
        return [child_size] * n_children

    # ---------- fill simulation ----------

    def simulate_fill(
        self,
        order: Order,
        mid_price: float,
        avg_volume: float,
        volatility: float,
    ) -> Order:
        """
        Fill the order at mid + slippage (for BUY) or mid - slippage (for SELL).
        Returns the same Order object with fill_price, commission, status updated.
        """
        slip_frac = self.compute_slippage(mid_price, order.size, avg_volume, volatility)
        if order.side == OrderSide.BUY:
            fill_price = mid_price * (1 + slip_frac)
        else:
            fill_price = mid_price * (1 - slip_frac)

        order.fill_price = fill_price
        order.slippage = abs(fill_price - mid_price) * order.size
        order.commission = self.commission_per_unit * order.size
        order.status = OrderStatus.FILLED
        return order

    # ---------- aggregate metrics ----------

    def round_trip_cost(
        self,
        order_size: float,
        mid_price: float,
        avg_volume: float,
        volatility: float,
    ) -> dict:
        """Estimate cost of a full round trip (open + close)."""
        one_way_slip = self.compute_slippage(mid_price, order_size, avg_volume, volatility)
        one_way_cost = one_way_slip * mid_price * order_size
        commission = self.commission_per_unit * order_size * 2
        return {
            "one_way_slippage_pct": one_way_slip,
            "one_way_cost": one_way_cost,
            "round_trip_cost": 2 * one_way_cost + commission,
            "commission": commission,
        }
