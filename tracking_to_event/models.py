from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable


EVENT_COLUMNS = [
    "Team",
    "Type",
    "Subtype",
    "Period",
    "Start Frame",
    "Start Time [s]",
    "End Frame",
    "End Time [s]",
    "From",
    "To",
    "Start X",
    "Start Y",
    "End X",
    "End Y",
]


@dataclass(slots=True, frozen=True)
class PlayerPosition:
    team: str
    number: str
    x: float
    y: float

    @property
    def label(self) -> str:
        return f"Player{self.number}"

    def as_tuple(self) -> tuple[float, float]:
        return (self.x, self.y)


@dataclass(slots=True, frozen=True)
class BallPosition:
    x: float
    y: float

    def as_tuple(self) -> tuple[float, float]:
        return (self.x, self.y)


@dataclass(slots=True)
class FrameRecord:
    period: int
    frame: int
    time_seconds: float
    ball: BallPosition
    players: list[PlayerPosition]


@dataclass(slots=True)
class PossessionSegment:
    period: int
    team: str
    player_label: str
    start_frame: int
    start_time: float
    start_xy: tuple[float, float]
    end_frame: int
    end_time: float
    end_xy: tuple[float, float]
    on_ball: tuple[str, ...] = field(default_factory=tuple)


@dataclass(slots=True)
class BallOutSegment:
    period: int
    start_frame: int
    start_time: float
    start_xy: tuple[float, float]
    end_frame: int
    end_time: float
    end_xy: tuple[float, float]


@dataclass(slots=True, frozen=True)
class EventRecord:
    team: str
    event_type: str
    subtype: str | None
    period: int
    start_frame: int
    start_time_seconds: float
    end_frame: int
    end_time_seconds: float
    from_player: str | None
    to_player: str | None
    start_x: float | None
    start_y: float | None
    end_x: float | None
    end_y: float | None

    def to_row(self) -> dict[str, object]:
        return {
            "Team": self.team,
            "Type": self.event_type,
            "Subtype": self.subtype,
            "Period": self.period,
            "Start Frame": self.start_frame,
            "Start Time [s]": round(self.start_time_seconds, 2),
            "End Frame": self.end_frame,
            "End Time [s]": round(self.end_time_seconds, 2),
            "From": self.from_player,
            "To": self.to_player,
            "Start X": _rounded(self.start_x),
            "Start Y": _rounded(self.start_y),
            "End X": _rounded(self.end_x),
            "End Y": _rounded(self.end_y),
        }


def events_to_rows(events: Iterable[EventRecord]) -> list[dict[str, object]]:
    return [event.to_row() for event in events]


def _rounded(value: float | None) -> float | None:
    if value is None:
        return None
    return round(value, 2)
