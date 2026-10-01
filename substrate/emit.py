# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 SnapKitty Collective
"""Canonical JSON emitter with provenance tags.

Every number in a result file carries a provenance tag:
  measured   — actually timed/observed on this machine in this run
  derived    — computed from measured or specified values (e.g. checksums)
  specified  — taken from the experiment spec / input config
  unknown    — not runnable here; emitted as null, never fabricated

Canonical form: json.dumps with sort_keys=True, indent=2, and a trailing
newline. Field elements are emitted as decimal strings to avoid any
JSON-number precision ambiguity; the schema documents this.
"""

from __future__ import annotations

import json

MEASURED = "measured"
DERIVED = "derived"
SPECIFIED = "specified"
UNKNOWN = "unknown"

SCHEMA_VERSION = "ra-bench/1"


def felt(x: int) -> str:
    """A field element as a decimal string (canonical, no precision loss)."""
    return str(int(x))


def measurement(value: object, provenance: str) -> dict[str, object]:
    assert provenance in (MEASURED, DERIVED, SPECIFIED, UNKNOWN)
    return {"value": value, "provenance": provenance}


def null_measurement() -> dict[str, object]:
    return measurement(None, UNKNOWN)


def canonical(payload: object) -> str:
    return json.dumps(payload, sort_keys=True, indent=2) + "\n"


def emit(path: str, payload: dict[str, object]) -> None:
    with open(path, "w") as f:
        f.write(canonical(payload))
