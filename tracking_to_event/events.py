from __future__ import annotations

from tracking_to_event.geometry import classify_out_side, is_goal_path
from tracking_to_event.models import BallOutSegment, EventRecord, PossessionSegment
from tracking_to_event.config import DetectorConfig


def generate_pass(previous_possession: PossessionSegment, next_possession: PossessionSegment) -> EventRecord:
    return EventRecord(
        team=next_possession.team,
        event_type="PASS",
        subtype=None,
        period=next_possession.period,
        start_frame=previous_possession.end_frame,
        start_time_seconds=previous_possession.end_time,
        end_frame=next_possession.start_frame,
        end_time_seconds=next_possession.start_time,
        from_player=previous_possession.player_label,
        to_player=next_possession.player_label,
        start_x=previous_possession.end_xy[0],
        start_y=previous_possession.end_xy[1],
        end_x=next_possession.start_xy[0],
        end_y=next_possession.start_xy[1],
    )


def generate_interception(previous_possession: PossessionSegment, next_possession: PossessionSegment) -> list[EventRecord]:
    return [
        EventRecord(
            team=previous_possession.team,
            event_type="BALL LOST",
            subtype="INTERCEPTION",
            period=previous_possession.period,
            start_frame=previous_possession.end_frame,
            start_time_seconds=previous_possession.end_time,
            end_frame=next_possession.start_frame,
            end_time_seconds=next_possession.start_time,
            from_player=previous_possession.player_label,
            to_player=None,
            start_x=previous_possession.end_xy[0],
            start_y=previous_possession.end_xy[1],
            end_x=next_possession.start_xy[0],
            end_y=next_possession.start_xy[1],
        ),
        EventRecord(
            team=next_possession.team,
            event_type="RECOVERY",
            subtype="INTERCEPTION",
            period=next_possession.period,
            start_frame=next_possession.start_frame,
            start_time_seconds=next_possession.start_time,
            end_frame=next_possession.start_frame,
            end_time_seconds=next_possession.start_time,
            from_player=next_possession.player_label,
            to_player=None,
            start_x=next_possession.start_xy[0],
            start_y=next_possession.start_xy[1],
            end_x=None,
            end_y=None,
        ),
    ]


def generate_ball_out(previous_possession: PossessionSegment, ball_out: BallOutSegment) -> EventRecord:
    return EventRecord(
        team=previous_possession.team,
        event_type="BALL OUT",
        subtype=None,
        period=previous_possession.period,
        start_frame=previous_possession.end_frame,
        start_time_seconds=previous_possession.end_time,
        end_frame=ball_out.end_frame,
        end_time_seconds=ball_out.end_time,
        from_player=previous_possession.player_label,
        to_player=None,
        start_x=previous_possession.end_xy[0],
        start_y=previous_possession.end_xy[1],
        end_x=ball_out.end_xy[0],
        end_y=ball_out.end_xy[1],
    )


def generate_set_piece(possession: PossessionSegment, subtype: str) -> EventRecord:
    return EventRecord(
        team=possession.team,
        event_type="SET PIECE",
        subtype=subtype,
        period=possession.period,
        start_frame=possession.start_frame,
        start_time_seconds=possession.start_time,
        end_frame=possession.start_frame,
        end_time_seconds=possession.start_time,
        from_player=possession.player_label,
        to_player=None,
        start_x=None,
        start_y=None,
        end_x=None,
        end_y=None,
    )


def generate_shot(previous_possession: PossessionSegment, ball_out: BallOutSegment) -> EventRecord:
    return EventRecord(
        team=previous_possession.team,
        event_type="SHOT",
        subtype="ON TARGET-GOAL",
        period=previous_possession.period,
        start_frame=previous_possession.end_frame,
        start_time_seconds=previous_possession.end_time,
        end_frame=ball_out.end_frame,
        end_time_seconds=ball_out.end_time,
        from_player=previous_possession.player_label,
        to_player=None,
        start_x=previous_possession.end_xy[0],
        start_y=previous_possession.end_xy[1],
        end_x=ball_out.end_xy[0],
        end_y=ball_out.end_xy[1],
    )


def restart_subtype(
    config: DetectorConfig,
    previous_team: str,
    next_team: str,
    ball_out: BallOutSegment,
) -> str | None:
    side = classify_out_side(ball_out.end_xy, config.ball_out_tolerance)
    if side == "touchline":
        return "THROW IN"
    if side == "goal_line":
        if next_team != previous_team:
            return "CORNER KICK"
        return "GOAL KICK"
    return None


def classify_ball_outcome(
    config: DetectorConfig,
    previous_possession: PossessionSegment,
    ball_out: BallOutSegment,
) -> str:
    if is_goal_path(previous_possession.end_xy, ball_out.end_xy, config):
        return "goal"
    return "ball_out"
