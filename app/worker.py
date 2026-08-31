import argparse
import time

from app.config import get_settings
from app.db import SessionLocal
from app.services.pipeline import run_next_job


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--once",
        action="store_true",
        help="Process at most one queued job.",
    )

    args = parser.parse_args()
    settings = get_settings()

    while True:
        found = run_next_job(
            SessionLocal
        )

        if args.once:
            return

        if not found:
            time.sleep(
                settings.worker_poll_seconds
            )


if __name__ == "__main__":
    main()
