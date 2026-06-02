#!/usr/bin/env python3
"""Generate pinned requirements lock files from pyproject.toml."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def _run_pip_compile(requirements_in: Path, requirements_out: Path) -> None:
    command = [
        sys.executable,
        "-m",
        "piptools",
        "compile",
        str(requirements_in),
        "--output-file",
        str(requirements_out),
        "--resolver=backtracking",
        "--strip-extras",
    ]
    subprocess.run(command, check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Compile pinned requirement lock files")
    parser.add_argument("--root", default=".", help="Repository root")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    prod_in = root / "requirements.in"
    dev_in = root / "requirements-dev.in"

    if not prod_in.exists():
        raise SystemExit(f"missing {prod_in}")

    _run_pip_compile(prod_in, root / "requirements.lock")
    if dev_in.exists():
        _run_pip_compile(dev_in, root / "requirements-dev.lock")

    print("Generated:")
    print(f"  {root / 'requirements.lock'}")
    if dev_in.exists():
        print(f"  {root / 'requirements-dev.lock'}")


if __name__ == "__main__":
    main()
