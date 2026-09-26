"""Hug Guardian: a booking-screening agent that rewrites its own harness."""

import sys
import types

# strands_harness_optimizer.optimizers imports strands_tools.shell, which needs the
# Unix-only `termios`. We never use its shell-based optimizer, so on Windows we
# stub that module to let the rest of the package (FormulaOptimizer etc.) import.
if sys.platform == "win32" and "strands_tools.shell" not in sys.modules:
    try:
        import strands_tools.shell  # noqa: F401
    except ModuleNotFoundError:
        stub = types.ModuleType("strands_tools.shell")
        stub.shell = None
        sys.modules["strands_tools.shell"] = stub

import logging

# Strands logs a warning per call about reasoning blocks over the Chat Completions API. Harmless noise.
logging.getLogger("strands").setLevel(logging.ERROR)
