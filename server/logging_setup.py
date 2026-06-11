"""Stdlib logging configuration for the betTube Studio API server.

Single stream handler to stdout so container platforms can collect logs
without extra agents. Level comes from BETTUBE_STUDIO_LOG_LEVEL (default
INFO). Deployments that need JSON or aggregated logging can swap the
formatter here without touching the rest of the server.
"""

from __future__ import annotations

import logging
import os
import sys

_CONFIGURED = False


def configure_logging() -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return

    level_name = str(os.getenv("BETTUBE_STUDIO_LOG_LEVEL") or "INFO").strip().upper()
    level = getattr(logging, level_name, logging.INFO)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))

    root = logging.getLogger()
    root.setLevel(level)
    if not any(isinstance(existing, logging.StreamHandler) for existing in root.handlers):
        root.addHandler(handler)

    _CONFIGURED = True
