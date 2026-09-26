"""Run the self-improvement loop.

    python scripts/loop.py              # 4 rounds, continue from the active harness
    python scripts/loop.py --rounds 6
    python scripts/loop.py --reset      # wipe the store and start again from v1
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from hug_guardian.loop import run_loop  # noqa: E402

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--rounds", type=int, default=4)
    p.add_argument("--reset", action="store_true")
    a = p.parse_args()
    run_loop(rounds=a.rounds, reset=a.reset, log=lambda s: print(s, flush=True))
