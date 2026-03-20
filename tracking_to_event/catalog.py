from __future__ import annotations

from pathlib import Path

from tracking_to_event.metrica import game_directory, reference_events_path, tracking_paths


def list_supported_games(data_dir: str | Path) -> list[dict[str, object]]:
    base = Path(data_dir)
    games: list[dict[str, object]] = []

    for directory in sorted(base.glob("Sample_Game_*")):
        try:
            game_id = int(directory.name.rsplit("_", 1)[-1])
        except ValueError:
            continue

        try:
            home_path, away_path = tracking_paths(base, game_id)
            events_path = reference_events_path(base, game_id)
        except FileNotFoundError:
            continue

        games.append(
            {
                "id": game_id,
                "label": f"Sample Game {game_id}",
                "format": "metrica",
                "directory": str(game_directory(base, game_id)),
                "home_tracking": home_path.name,
                "away_tracking": away_path.name,
                "reference_events": events_path.name,
            }
        )

    return games
