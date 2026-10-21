#!/usr/bin/env python3
"""OBC script — CLI."""

from __future__ import annotations

import argparse
import sys

from satellite.persistence import load_simulator, save_simulator


def parse_panel_index(raw: str) -> int:
    """Additional validation redundancy in case of strange arg's format."""
    if raw.startswith("--panelIndex="):
        raw = raw.split("=", 1)[1]
    return int(raw)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Trigger HDRM for a solar panel.")
    parser.add_argument(
        "--panelIndex",
        type=parse_panel_index,
        required=True,
        help="Panel index (1-4 in basic version).",
    )
    args = parser.parse_args(argv)

    sim = load_simulator()
    accepted = sim.release_panel(args.panelIndex)
    save_simulator(sim)

    print("TRUE" if accepted else "FALSE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
