from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from tracking_to_event.config import DetectorConfig
from tracking_to_event.geometry import distance, is_ball_out
from tracking_to_event.models import BallOutSegment, FrameRecord, PlayerPosition, PossessionSegment


@dataclass(slots=True)
class _ActivePossession:
    period: int
    team: str
    player_label: str
    start_frame: int
    start_time: float
    start_xy: tuple[float, float]
    end_frame: int
    end_time: float
    end_xy: tuple[float, float]
    on_ball: tuple[str, ...]

    def touch(self, frame: FrameRecord, on_ball: tuple[str, ...]) -> None:
        self.end_frame = frame.frame
        self.end_time = frame.time_seconds
        self.end_xy = frame.ball.as_tuple()
        self.on_ball = on_ball

    def finalize(self) -> PossessionSegment:
        return PossessionSegment(
            period=self.period,
            team=self.team,
            player_label=self.player_label,
            start_frame=self.start_frame,
            start_time=self.start_time,
            start_xy=self.start_xy,
            end_frame=self.end_frame,
            end_time=self.end_time,
            end_xy=self.end_xy,
            on_ball=self.on_ball,
        )


@dataclass(slots=True)
class _PendingSwitch:
    player: PlayerPosition
    start_frame: int
    start_time: float
    start_xy: tuple[float, float]
    on_ball: tuple[str, ...]
    streak: int = 1

    def touch(self, frame: FrameRecord, on_ball: tuple[str, ...]) -> None:
        self.on_ball = on_ball
        self.streak += 1

    def to_active(self) -> _ActivePossession:
        return _ActivePossession(
            period=0,
            team=self.player.team,
            player_label=self.player.label,
            start_frame=self.start_frame,
            start_time=self.start_time,
            start_xy=self.start_xy,
            end_frame=self.start_frame,
            end_time=self.start_time,
            end_xy=self.start_xy,
            on_ball=self.on_ball,
        )


def detect_segments(frames: Iterable[FrameRecord], config: DetectorConfig) -> list[PossessionSegment | BallOutSegment]:
    segments: list[PossessionSegment | BallOutSegment] = []
    active_possession: _ActivePossession | None = None
    active_ball_out: BallOutSegment | None = None
    pending_switch: _PendingSwitch | None = None

    for frame in frames:
        controller, on_ball = detect_controller(frame, config, active_possession.player_label if active_possession else None)
        ball_xy = frame.ball.as_tuple()
        out_of_bounds = is_ball_out(ball_xy, tolerance=config.ball_out_tolerance)

        if active_ball_out is not None:
            if out_of_bounds:
                active_ball_out.end_frame = frame.frame
                active_ball_out.end_time = frame.time_seconds
                active_ball_out.end_xy = ball_xy
                continue
            segments.append(active_ball_out)
            active_ball_out = None
            pending_switch = None

        if out_of_bounds:
            if active_possession is not None:
                segments.append(active_possession.finalize())
                active_possession = None

            active_ball_out = BallOutSegment(
                period=frame.period,
                start_frame=frame.frame,
                start_time=frame.time_seconds,
                start_xy=ball_xy,
                end_frame=frame.frame,
                end_time=frame.time_seconds,
                end_xy=ball_xy,
            )
            pending_switch = None
            continue

        if controller is None:
            pending_switch = None
            continue

        if active_possession is None:
            active_possession = _start_possession(frame, controller, on_ball)
            pending_switch = None
            continue

        if active_possession.player_label == controller.label:
            active_possession.touch(frame, on_ball)
            pending_switch = None
            continue

        if pending_switch is not None and pending_switch.player.label == controller.label:
            pending_switch.touch(frame, on_ball)
        else:
            pending_switch = _PendingSwitch(
                player=controller,
                start_frame=frame.frame,
                start_time=frame.time_seconds,
                start_xy=ball_xy,
                on_ball=on_ball,
            )

        if pending_switch.streak >= config.switch_confirmation_frames:
            segments.append(active_possession.finalize())
            active_possession = _start_possession(frame, controller, on_ball)
            active_possession.start_frame = pending_switch.start_frame
            active_possession.start_time = pending_switch.start_time
            active_possession.start_xy = pending_switch.start_xy
            pending_switch = None

    if active_ball_out is not None:
        segments.append(active_ball_out)
    if active_possession is not None:
        segments.append(active_possession.finalize())

    return segments


def detect_controller(
    frame: FrameRecord,
    config: DetectorConfig,
    active_player_label: str | None = None,
) -> tuple[PlayerPosition | None, tuple[str, ...]]:
    distances = sorted(
        (
            (player, distance(player.as_tuple(), frame.ball.as_tuple()))
            for player in frame.players
        ),
        key=lambda item: item[1],
    )

    on_ball = tuple(player.label for player, player_distance in distances if player_distance <= config.competing_radius)
    if not distances:
        return None, on_ball

    if active_player_label is not None:
        for player, player_distance in distances:
            if player.label == active_player_label and player_distance <= config.sticky_radius:
                return player, on_ball

    nearest_player, nearest_distance = distances[0]
    if nearest_distance <= config.control_radius:
        return nearest_player, on_ball

    return None, on_ball


def _start_possession(frame: FrameRecord, player: PlayerPosition, on_ball: tuple[str, ...]) -> _ActivePossession:
    ball_xy = frame.ball.as_tuple()
    return _ActivePossession(
        period=frame.period,
        team=player.team,
        player_label=player.label,
        start_frame=frame.frame,
        start_time=frame.time_seconds,
        start_xy=ball_xy,
        end_frame=frame.frame,
        end_time=frame.time_seconds,
        end_xy=ball_xy,
        on_ball=on_ball,
    )
