"""Reporter - formats backtest results for terminal + files."""
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any


def format_metrics_block(result: Dict[str, Any], symbol: str, timeframe: str) -> str:
    s = result["stats"]
    lines = []
    lines.append("=" * 62)
    lines.append(f"BETA BRAIN BACKTEST - {symbol} {timeframe}")
    lines.append("=" * 62)
    lines.append(f"Period:        {result.get('start_iso', '?')} -> {result.get('end_iso', '?')}")
    lines.append(f"Candles:       {result.get('total_candles', 0)}")
    lines.append(f"Runtime:       {result.get('runtime_sec', 0):.1f}s")
    lines.append(f"Warmup:        {result.get('warmup', 0)} candles")
    lines.append("")
    lines.append("------------------- HEADLINE -------------------")
    lines.append(f"Starting balance:    ${s['starting_balance']:.2f}")
    lines.append(f"Ending balance:      ${s['ending_balance']:.2f}")
    lines.append(f"Net PnL:             ${s['net_pnl']:+.2f} ({s.get('return_pct', 0):+.2f}%)")
    lines.append(f"Peak balance:        ${s['peak_balance']:.2f}")
    lines.append(f"Max drawdown:        ${s['max_drawdown_usd']:.2f} ({s['max_drawdown_pct']:.2f}%)")
    lines.append("")
    lines.append(f"Total trades:        {s['total_trades']}")
    lines.append(f"Wins / Losses / Flat: {s['wins']} / {s['losses']} / {s['flat']}")
    lines.append(f"Win rate:            {s['win_rate']:.2f}%")
    lines.append(f"Profit factor:       {s['profit_factor']}")
    lines.append(f"Avg win / avg loss:  ${s['avg_win']:.2f} / ${s['avg_loss']:.2f}")
    if "expectancy_usd" in s:
        lines.append(f"Expectancy/trade:    ${s['expectancy_usd']:+.2f}")
    lines.append("")
    if "sharpe" in s:
        lines.append(f"Sharpe:              {s['sharpe']}")
    if "sortino" in s:
        lines.append(f"Sortino:             {s['sortino']}")
    if "calmar" in s:
        lines.append(f"Calmar:              {s['calmar']}")
    lines.append("")
    lines.append(f"Exits TP/SL/TMO/EOD: {s['exits_tp']} / {s['exits_sl']} / {s['exits_timeout']} / {s['exits_eod']}")
    lines.append("")
    return "\n".join(lines)


def format_strategy_table(analyzer_dict: Dict[str, Any]) -> str:
    strats = analyzer_dict.get("strategies", {})
    if not strats:
        return "------------------- PER-STRATEGY -------------------\n(no trades)\n"
    rows = sorted(strats.items(), key=lambda kv: -kv[1].get("net_pnl", 0))
    lines = []
    lines.append("------------------- PER-STRATEGY -------------------")
    lines.append(f"{'Strategy':<22} {'Trades':>7} {'Wins':>6} {'Loss':>6} {'WR%':>7} {'PnL':>11} {'Avg':>9}")
    lines.append("-" * 62)
    for name, rec in rows:
        lines.append(
            f"{name:<22} {rec['trades']:>7} {rec['wins']:>6} {rec['losses']:>6} "
            f"{rec['win_rate']:>6.1f}% {rec['net_pnl']:>10.2f} {rec['avg_pnl_per_trade']:>8.2f}"
        )
    lines.append("")
    return "\n".join(lines)


def format_regime_table(analyzer_dict: Dict[str, Any]) -> str:
    regimes = analyzer_dict.get("regimes", {})
    if not regimes:
        return "------------------- PER-REGIME -------------------\n(no trades)\n"
    # Aggregate per-regime (sum across strategies)
    agg: Dict[str, Dict[str, float]] = {}
    for regime, strats in regimes.items():
        total_trades = 0
        total_wins = 0
        total_pnl = 0.0
        for sname, rec in strats.items():
            total_trades += rec.get("trades", 0)
            total_wins += rec.get("wins", 0)
            total_pnl += rec.get("net_pnl", 0.0)
        agg[regime] = {
            "trades": total_trades,
            "wins": total_wins,
            "net_pnl": total_pnl,
            "wr": (total_wins / total_trades * 100) if total_trades > 0 else 0.0,
            "avg": (total_pnl / total_trades) if total_trades > 0 else 0.0,
        }
    lines = []
    lines.append("------------------- PER-REGIME -------------------")
    lines.append(f"{'Regime':<18} {'Trades':>7} {'WR%':>7} {'PnL':>11} {'Avg':>9}")
    lines.append("-" * 62)
    for regime, rec in sorted(agg.items(), key=lambda kv: -kv[1]["net_pnl"]):
        lines.append(
            f"{regime:<18} {rec['trades']:>7} {rec['wr']:>6.1f}% "
            f"{rec['net_pnl']:>10.2f} {rec['avg']:>8.2f}"
        )
    lines.append("")
    return "\n".join(lines)


def build_full_report(result: Dict[str, Any], analyzer_dict: Dict[str, Any],
                     symbol: str, timeframe: str) -> str:
    parts = [
        format_metrics_block(result, symbol, timeframe),
        format_strategy_table(analyzer_dict),
        format_regime_table(analyzer_dict),
        "=" * 62,
    ]
    return "\n".join(parts)


def write_report_files(report_text: str, result: Dict[str, Any],
                      analyzer_dict: Dict[str, Any], trades: list,
                      symbol: str, out_dir: str = "data/logs") -> Dict[str, str]:
    """Write .txt, .json, and _trades.csv to out_dir. Returns paths dict."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%d_%H%M")

    base = f"backtest_beta_{symbol}_{stamp}"
    txt_path = out_dir / f"{base}.txt"
    json_path = out_dir / f"{base}.json"
    csv_path = out_dir / f"{base}_trades.csv"

    txt_path.write_text(report_text, encoding="utf-8")

    payload = {
        "symbol": symbol,
        "result": {
            "start_iso": result.get("start_iso"),
            "end_iso": result.get("end_iso"),
            "total_candles": result.get("total_candles"),
            "warmup": result.get("warmup"),
            "runtime_sec": result.get("runtime_sec"),
            "stats": result.get("stats"),
        },
        "analyzer": analyzer_dict,
    }
    json_path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")

    # CSV
    if trades:
        headers = list(trades[0].keys())
        lines = [",".join(headers)]
        for t in trades:
            row = []
            for h in headers:
                v = t.get(h, "")
                if isinstance(v, list):
                    v = "|".join(str(x) for x in v)
                row.append(str(v))
            lines.append(",".join(row))
        csv_path.write_text("\n".join(lines), encoding="utf-8")
    else:
        csv_path.write_text("no_trades\n", encoding="utf-8")

    return {
        "txt": str(txt_path),
        "json": str(json_path),
        "csv": str(csv_path),
    }
