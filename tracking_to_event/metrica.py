from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterator

from tracking_to_event.models import BallPosition, FrameRecord, PlayerPosition


def game_directory(data_dir: str | Path, game_id: int) -> Path:
    return Path(data_dir) / f"Sample_Game_{game_id}"


def tracking_paths(data_dir: str | Path, game_id: int) -> tuple[Path, Path]:
    base = game_directory(data_dir, game_id)
    home_path = base / f"Sample_Game_{game_id}_RawTrackingData_Home_Team.csv"
    away_path = base / f"Sample_Game_{game_id}_RawTrackingData_Away_Team.csv"
    if not home_path.exists() or not away_path.exists():
        raise FileNotFoundError(f"Could not find Metrica tracking files for game {game_id} in {base}")
    return home_path, away_path


def reference_events_path(data_dir: str | Path, game_id: int) -> Path:
    path = game_directory(data_dir, game_id) / f"Sample_Game_{game_id}_RawEventsData.csv"
    if not path.exists():
        raise FileNotFoundError(f"Could not find Metrica reference events for game {game_id}: {path}")
    return path


def iter_metrica_frames(
    data_dir: str | Path,
    game_id: int,
    start_frame: int | None = None,
    end_frame: int | None = None,
) -> Iterator[FrameRecord]:
    home_path, away_path = tracking_paths(data_dir, game_id)
    return iter_metrica_frames_from_paths(home_path, away_path, start_frame, end_frame)


def iter_metrica_frames_from_paths(
    home_path: str | Path,
    away_path: str | Path,
    start_frame: int | None = None,
    end_frame: int | None = None,
) -> Iterator[FrameRecord]:
    with Path(home_path).open(newline="") as home_file, Path(away_path).open(newline="") as away_file:
        home_reader = csv.reader(home_file)
        away_reader = csv.reader(away_file)

        home_headers = _read_tracking_headers(home_reader)
        away_headers = _read_tracking_headers(away_reader)

        for home_row, away_row in zip(home_reader, away_reader):
            if not home_row or not away_row:
                continue

            frame_number = int(home_row[1])
            if start_frame is not None and frame_number < start_frame:
                continue
            if end_frame is not None and frame_number > end_frame:
                break

            away_frame_number = int(away_row[1])
            if frame_number != away_frame_number:
                raise ValueError(f"Mismatched frame numbers: {frame_number} != {away_frame_number}")

            period = int(home_row[0])
            away_period = int(away_row[0])
            if period != away_period:
                raise ValueError(f"Mismatched periods for frame {frame_number}: {period} != {away_period}")

            time_seconds = float(home_row[2])
            players = _players_from_row(home_row, home_headers) + _players_from_row(away_row, away_headers)
            ball = _ball_from_rows(home_row, away_row)
            if ball is None:
                continue

            yield FrameRecord(
                period=period,
                frame=frame_number,
                time_seconds=time_seconds,
                ball=ball,
                players=players,
            )


def _read_tracking_headers(reader: csv.reader) -> dict[str, object]:
    team_row = next(reader)
    player_row = next(reader)
    next(reader)

    team_name = next(value for value in team_row[3:] if value)
    player_numbers = [value for value in player_row[3::2] if value]
    return {"team_name": team_name, "player_numbers": player_numbers}


def _players_from_row(row: list[str], headers: dict[str, object]) -> list[PlayerPosition]:
    team_name = str(headers["team_name"])
    player_numbers = list(headers["player_numbers"])
    players: list[PlayerPosition] = []
    for index, player_number in enumerate(player_numbers):
        x_value = row[3 + index * 2]
        y_value = row[4 + index * 2]
        if _is_missing(x_value) or _is_missing(y_value):
            continue
        players.append(
            PlayerPosition(
                team=team_name,
                number=player_number,
                x=float(x_value),
                y=float(y_value),
            )
        )
    return players


def _ball_from_rows(home_row: list[str], away_row: list[str]) -> BallPosition | None:
    if not _is_missing(home_row[-2]) and not _is_missing(home_row[-1]):
        return BallPosition(float(home_row[-2]), float(home_row[-1]))
    if not _is_missing(away_row[-2]) and not _is_missing(away_row[-1]):
        return BallPosition(float(away_row[-2]), float(away_row[-1]))
    return None


def _is_missing(value: str) -> bool:
    return value == "" or value == "NaN"
