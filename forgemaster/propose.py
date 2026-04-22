"""
CLI: create a new proposal for CEO + Legion review.

Usage:
    python forgemaster/propose.py --title "..." --type feature \
        --description "..." [--proposer forgemaster] [--review-now]
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import proposals as prop_store


def main():
    parser = argparse.ArgumentParser(description="Create a new proposal.")
    parser.add_argument("--title", required=True)
    parser.add_argument("--description", required=True, help="What are we shipping? Why? Cost? Risk?")
    parser.add_argument("--type", required=True, choices=["feature", "product", "pricing", "content", "infra", "positioning", "partnership"])
    parser.add_argument("--proposer", default="pedro")
    parser.add_argument("--file", help="Read description from file instead of --description")
    parser.add_argument("--review-now", action="store_true", help="Also run legion + CEO immediately")
    args = parser.parse_args()

    description = args.description
    if args.file:
        description = Path(args.file).read_text(encoding="utf-8")

    p = prop_store.create(title=args.title, description=description, ptype=args.type, proposer=args.proposer)
    print(f"Created proposal {p.id}")
    print(f"  status: {p.status}")

    if args.review_now:
        from ceo_agent import review_proposal
        r = review_proposal(p.id)
        print("\n=== CEO decision ===")
        print(json.dumps(r["decision"], indent=2))
        print("\n=== Legion brief ===")
        print(r["legion"]["brief"])


if __name__ == "__main__":
    main()
