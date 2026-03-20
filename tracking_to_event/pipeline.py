from __future__ import annotations

from pathlib import Path

import pandas as pd

from tracking_to_event.config import DetectorConfig
from tracking_to_event.detector import detect_segments
from tracking_to_event.events import (
    classify_ball_outcome,
    generate_ball_out,
    generate_interception,
    generate_pass,
    generate_set_piece,
    generate_shot,
    restart_subtype,
)
from tracking_to_event.metrica import iter_metrica_frames, iter_metrica_frames_from_paths
from tracking_to_event.models import BallOutSegment, EVENT_COLUMNS, EventRecord, PossessionSegment, events_to_rows


def generate_events_for_game(
    data_dir: str | Path,
    game_id: int,
    input_format: str = "metrica",
    start_frame: int | None = None,
    end_frame: int | None = None,
    config: DetectorConfig | None = None,
) -> list[EventRecord]:
    if input_format != "metrica":
        raise ValueError(f"Unsupported input format: {input_format}")

    detector_config = config or DetectorConfig()
    frames = iter_metrica_frames(data_dir, game_id, start_frame=start_frame, end_frame=end_frame)
    segments = detect_segments(frames, detector_config)
    return build_events_from_segments(segments, detector_config)


def generate_events_from_paths(
    home_path: str | Path,
    away_path: str | Path,
    input_format: str = "metrica",
    start_frame: int | None = None,
    end_frame: int | None = None,
    config: DetectorConfig | None = None,
) -> list[EventRecord]:
    if input_format != "metrica":
        raise ValueError(f"Unsupported input format: {input_format}")

    detector_config = config or DetectorConfig()
    frames = iter_metrica_frames_from_paths(home_path, away_path, start_frame=start_frame, end_frame=end_frame)
    segments = detect_segments(frames, detector_config)
    return build_events_from_segments(segments, detector_config)


def generate_dataframe_for_game(
    data_dir: str | Path,
    game_id: int,
    input_format: str = "metrica",
    start_frame: int | None = None,
    end_frame: int | None = None,
    config: DetectorConfig | None = None,
) -> pd.DataFrame:
    events = generate_events_for_game(
        data_dir=data_dir,
        game_id=game_id,
        input_format=input_format,
        start_frame=start_frame,
        end_frame=end_frame,
        config=config,
    )
    return pd.DataFrame(events_to_rows(events), columns=EVENT_COLUMNS)


def generate_dataframe_from_paths(
    home_path: str | Path,
    away_path: str | Path,
    input_format: str = "metrica",
    start_frame: int | None = None,
    end_frame: int | None = None,
    config: DetectorConfig | None = None,
) -> pd.DataFrame:
    events = generate_events_from_paths(
        home_path=home_path,
        away_path=away_path,
        input_format=input_format,
        start_frame=start_frame,
        end_frame=end_frame,
        config=config,
    )
    return pd.DataFrame(events_to_rows(events), columns=EVENT_COLUMNS)


def build_events_from_segments(
    segments: list[PossessionSegment | BallOutSegment],
    config: DetectorConfig,
) -> list[EventRecord]:
    events: list[EventRecord] = []
    previous_possession: PossessionSegment | None = None
    seen_periods: set[int] = set()
    pending_restart: dict[str, object] | None = None

    for segment in segments:
        if isinstance(segment, BallOutSegment):
            if previous_possession is None:
                continue

            outcome = classify_ball_outcome(config, previous_possession, segment)
            if outcome == "goal":
                events.append(generate_shot(previous_possession, segment))
                pending_restart = {"kind": "kickoff_after_goal", "period": segment.period}
            else:
                events.append(generate_ball_out(previous_possession, segment))
                pending_restart = {
                    "kind": "restart_after_ball_out",
                    "period": segment.period,
                    "ball_out": segment,
                    "previous_team": previous_possession.team,
                }
            previous_possession = None
            continue

        if segment.period not in seen_periods:
            events.append(generate_set_piece(segment, "KICK OFF"))
            seen_periods.add(segment.period)
            pending_restart = None
        elif pending_restart is not None:
            subtype = _resolve_restart_subtype(config, pending_restart, segment)
            if subtype is not None:
                events.append(generate_set_piece(segment, subtype))
            pending_restart = None

        if previous_possession is not None:
            if previous_possession.team == segment.team:
                events.append(generate_pass(previous_possession, segment))
            else:
                events.extend(generate_interception(previous_possession, segment))

        previous_possession = segment

    return events


def write_events_csv(events: list[EventRecord], output_path: str | Path) -> pd.DataFrame:
    dataframe = pd.DataFrame(events_to_rows(events), columns=EVENT_COLUMNS)
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    dataframe.to_csv(output, index=False)
    return dataframe


def _resolve_restart_subtype(
    config: DetectorConfig,
    pending_restart: dict[str, object],
    next_possession: PossessionSegment,
) -> str | None:
    kind = pending_restart["kind"]
    if kind == "kickoff_after_goal":
        return "KICK OFF"
    if kind != "restart_after_ball_out":
        return None

    ball_out = pending_restart["ball_out"]
    previous_team = str(pending_restart["previous_team"])
    assert isinstance(ball_out, BallOutSegment)
    return restart_subtype(config, previous_team, next_possession.team, ball_out)
