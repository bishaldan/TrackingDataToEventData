from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class DetectorConfig:
    control_radius: float = 0.025
    sticky_radius: float = 0.04
    competing_radius: float = 0.05
    switch_confirmation_frames: int = 3
    ball_out_tolerance: float = 0.0
    goal_y_min: float = 0.44
    goal_y_max: float = 0.56

    @classmethod
    def from_path(cls, path: str | Path | None) -> "DetectorConfig":
        if path is None:
            return cls()

        payload = json.loads(Path(path).read_text())
        valid_keys = set(asdict(cls()).keys())
        unknown_keys = set(payload) - valid_keys
        if unknown_keys:
            names = ", ".join(sorted(unknown_keys))
            raise ValueError(f"Unknown config keys: {names}")

        return cls(**payload)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)
