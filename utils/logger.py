"""
Structured logging for Quantum Stone Capital.
Uses loguru for rotation, colored console, and structured JSON logs.
"""
import sys
from pathlib import Path
from loguru import logger as _logger


def setup_logger(
    name: str = "qsc",
    log_dir: str = "logs",
    level: str = "INFO",
    rotation: str = "10 MB",
    retention: str = "30 days",
    json_logs: bool = True,
):
    """
    Configure and return a logger instance.

    Args:
        name: logger name (used for the log filename)
        log_dir: directory for log files (auto-created)
        level: console log level (DEBUG/INFO/WARNING/ERROR)
        rotation: log file rotation size/time
        retention: how long to keep old logs
        json_logs: also emit machine-readable JSON logs

    Returns:
        A configured loguru logger.
    """
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    # Remove default handler
    _logger.remove()

    # Console handler — human-readable, colored
    _logger.add(
        sys.stderr,
        level=level,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "<level>{message}</level>"
        ),
        colorize=True,
        backtrace=True,
        diagnose=False,  # don't leak variables in production
    )

    # File handler — human-readable
    _logger.add(
        log_path / f"{name}.log",
        level=level,
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} | {message}",
        rotation=rotation,
        retention=retention,
        compression="zip",
        encoding="utf-8",
        enqueue=True,  # thread-safe
    )

    # File handler — machine-readable JSON
    if json_logs:
        _logger.add(
            log_path / f"{name}_json.log",
            level=level,
            serialize=True,
            rotation=rotation,
            retention=retention,
            compression="zip",
            encoding="utf-8",
            enqueue=True,
        )

    return _logger


# Module-level convenience logger
logger = setup_logger()


def get_logger(module_name: str):
    """Return a child logger bound to a module name."""
    return logger.bind(module=module_name)
