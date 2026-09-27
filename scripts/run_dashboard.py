"""
Dashboard entry point with integrated brain loop.

Usage:
    python -m scripts.run_dashboard                # serve dashboard + brain loop
    python -m scripts.run_dashboard --no-brain     # dashboard only

Dashboard: http://localhost:8000
"""
import argparse
import threading
import time

import uvicorn

from utils.logger import logger


def start_brain_thread(interval: int = 30):
    """Start the brain loop in a background thread."""
    def loop():
        from dashboard.state import get_state
        from core.main_brain_v2 import MainBrainV2
        from scripts.run_brain import run_once

        state = get_state()
        brain = MainBrainV2()
        logger.info("Brain thread starting (interval=" + str(interval) + "s)")
        while True:
            try:
                n = run_once(brain, state)
                logger.info("Brain pass: " + str(n) + " decisions")
            except Exception as e:
                logger.error("Brain thread error: " + str(e))
            time.sleep(interval)

    t = threading.Thread(target=loop, daemon=True)
    t.start()
    return t


def main():
    parser = argparse.ArgumentParser(description="QSC Dashboard + Brain")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--no-brain", action="store_true", help="Skip the brain loop")
    parser.add_argument("--brain-interval", type=int, default=30)
    parser.add_argument("--reload", action="store_true", help="Auto-reload on file change")
    args = parser.parse_args()

    if not args.no_brain:
        start_brain_thread(interval=args.brain_interval)

    logger.info("Starting dashboard on http://" + args.host + ":" + str(args.port))
    uvicorn.run(
        "dashboard.app:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
    )


if __name__ == "__main__":
    main()
