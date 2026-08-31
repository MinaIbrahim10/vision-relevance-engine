import json
from pathlib import Path

from app.db import SessionLocal
from app.services.evaluator import (
    evaluate_top1,
)


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "artifacts" / "evaluation.json"


def main():
    db = SessionLocal()

    try:
        result = evaluate_top1(
            db
        )
    finally:
        db.close()

    OUTPUT.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    OUTPUT.write_text(
        json.dumps(
            result,
            indent=2,
        )
    )

    print(
        json.dumps(
            {
                "metric": result["metric"],
                "total": result["total"],
                "correct": result["correct"],
                "precision": (
                    result["precision"]
                ),
            },
            indent=2,
        )
    )

    print(
        f"Full report: {OUTPUT}"
    )


if __name__ == "__main__":
    main()
