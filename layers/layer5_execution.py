"""Layer 5 - Execution. Wraps ExecutionEngine."""
from core.execution_engine import ExecutionEngine


class Layer5Execution:
    def __init__(self, config_path: str = "config/master.yaml"):
        import yaml
        with open(config_path) as f:
            config = yaml.safe_load(f)
        exec_cfg = config.get("execution", {})
        self.engine = ExecutionEngine(
            slippage_model=exec_cfg.get("slippage_model", "linear"),
            max_slippage_pct=exec_cfg.get("max_slippage_pct", 0.001),
        )

    def split(self, size, avg_volume):
        return self.engine.split_order(size, avg_volume)

    def fill(self, order, mid, avg_volume, volatility):
        return self.engine.simulate_fill(order, mid, avg_volume, volatility)

    def round_trip_cost(self, size, mid, avg_volume, volatility):
        return self.engine.round_trip_cost(size, mid, avg_volume, volatility)
