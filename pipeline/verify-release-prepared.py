# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
"""Require successful release preparation for the selected tag before publication."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Optional


def find_prepared_run(runs: list[dict[str, Any]], tag: str, commit: str) -> Optional[str]:
    """Match a mainline push by commit or a tag dispatch by its fixed run title."""
    for run in runs:
        if run.get("conclusion") != "success" or run.get("headBranch") != "mainline":
            continue
        matches_push = run.get("event") == "push" and run.get("headSha") == commit
        matches_dispatch = (
            run.get("event") == "workflow_dispatch"
            and run.get("displayTitle") == f"Release: Prepare {tag}"
        )
        if (matches_push or matches_dispatch) and run.get("url"):
            return str(run["url"])
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--runs-file", required=True, type=Path)
    args = parser.parse_args()
    runs = json.loads(args.runs_file.read_text())
    if not isinstance(runs, list) or any(not isinstance(run, dict) for run in runs):
        parser.error("Expected a JSON array of workflow runs.")
    url = find_prepared_run(runs, args.tag, args.commit)
    if url is None:
        parser.exit(
            1,
            f"No successful Release: Prepare run for {args.tag} ({args.commit}). "
            "Run Release: Prepare for the tag before publication.\n",
        )
    print(url)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
