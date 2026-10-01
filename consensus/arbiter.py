"""ConsensusArbiter - reconciles QSC Brain and Beta Brain."""
from dataclasses import dataclass, field, asdict
from pathlib import Path
import yaml
from loguru import logger
from consensus.agreement import normalize_direction, agreement_label


DEFAULT_MULT = {
    "BOTH_AGREE": 1.0, "QSC_ONLY": 0.5, "BETA_ONLY": 0.5,
    "DISAGREE": 0.0, "BOTH_HOLD": 0.0,
}


@dataclass
class ArbiterDecision:
    consensus: str
    direction: str
    size_multiplier: float
    qsc_direction: str
    qsc_confidence: float
    beta_direction: str
    beta_confidence: float
    beta_regime: str = ""
    notes: list = field(default_factory=list)

    def to_dict(self):
        return asdict(self)

    @property
    def is_trade(self):
        return self.direction in ("LONG", "SHORT") and self.size_multiplier > 0.0


class ConsensusArbiter:
    def __init__(self, config_path="config/consensus.yaml"):
        self.config_path = config_path
        self.size_multiplier = dict(DEFAULT_MULT)
        self.beta_disable_regimes = ["CHOPPY"]
        self.qsc_disable_regimes = []
        self.priority = "qsc"
        self._load_config()

    def _load_config(self):
        path = Path(self.config_path)
        if not path.exists():
            logger.warning("ConsensusArbiter: no config at " + self.config_path)
            return
        try:
            with open(path, "r", encoding="utf-8-sig") as f:
                cfg = yaml.safe_load(f) or {}
            arb = cfg.get("arbiter", {})
            sm = arb.get("size_multiplier", {})
            for key, val in sm.items():
                self.size_multiplier[key.upper()] = float(val)
            self.beta_disable_regimes = arb.get("beta_disable_regimes", ["CHOPPY"])
            self.qsc_disable_regimes = arb.get("qsc_disable_regimes", [])
            self.priority = arb.get("priority", "qsc")
        except Exception as e:
            logger.error("ConsensusArbiter: config load failed: " + str(e))

    def decide(self, qsc_result, beta_verdict):
        qsc_decision = getattr(qsc_result, "decision", "no_trade") if qsc_result else "no_trade"
        qsc_dir = normalize_direction(getattr(qsc_result, "direction", None) if qsc_result else None)
        qsc_conf = float(getattr(qsc_result, "confidence", 0.0) or 0.0) if qsc_result else 0.0
        if qsc_decision != "trade":
            qsc_dir = "HOLD"

        beta_dir = "HOLD"
        beta_conf = 0.0
        beta_regime = ""
        if beta_verdict is not None:
            beta_winner = getattr(beta_verdict, "debate_winner", None)
            if getattr(beta_verdict, "final_decision", "REJECTED") == "APPROVED":
                beta_dir = normalize_direction(beta_winner)
                beta_conf = float(getattr(beta_verdict, "debate_confidence", 0.0) or 0.0)

        if beta_regime and beta_regime in self.beta_disable_regimes:
            beta_dir = "HOLD"
            beta_conf = 0.0

        consensus = agreement_label(qsc_dir, beta_dir)
        multiplier = self.size_multiplier.get(consensus, 0.0)

        if consensus == "BOTH_AGREE":
            final_dir = qsc_dir
            notes = ["both agree on " + qsc_dir]
        elif consensus == "QSC_ONLY":
            final_dir = qsc_dir
            notes = ["QSC edge, Beta silent"]
        elif consensus == "BETA_ONLY":
            final_dir = beta_dir
            notes = ["Beta edge, QSC silent"]
        elif consensus == "DISAGREE":
            final_dir = "HOLD"
            notes = ["conflict QSC=" + qsc_dir + " Beta=" + beta_dir]
            multiplier = 0.0
        else:
            final_dir = "HOLD"
            notes = ["both silent"]
            multiplier = 0.0

        return ArbiterDecision(
            consensus=consensus, direction=final_dir,
            size_multiplier=multiplier,
            qsc_direction=qsc_dir, qsc_confidence=qsc_conf,
            beta_direction=beta_dir, beta_confidence=beta_conf,
            beta_regime=beta_regime, notes=notes,
        )
