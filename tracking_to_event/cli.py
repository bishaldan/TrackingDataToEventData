from __future__ import annotations

import argparse
from pathlib import Path

import pytest
import uvicorn

from tracking_to_event.config import DetectorConfig
from tracking_to_event.pipeline import generate_events_for_game, write_events_csv
from tracking_to_event.validation import validate_game
from tracking_to_event.web import create_app


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "generate":
        config = DetectorConfig.from_path(args.config)
        events = generate_events_for_game(
            data_dir=args.data_dir,
            game_id=args.game_id,
            input_format=args.format,
            start_frame=args.start_frame,
            end_frame=args.end_frame,
            config=config,
        )
        dataframe = write_events_csv(events, args.output)
        print(f"Wrote {len(dataframe)} events to {Path(args.output)}")
        return 0

    if args.command == "validate":
        config = DetectorConfig.from_path(args.config)
        report = validate_game(
            data_dir=args.data_dir,
            game_id=args.game_id,
            input_format=args.format,
            start_frame=args.start_frame,
            end_frame=args.end_frame,
            config=config,
            generated_output_path=args.output,
        )
        print(report.render())
        return 0

    if args.command == "test":
        return int(pytest.main(["-q"]))

    if args.command == "serve":
        app = create_app(data_dir=args.data_dir)
        uvicorn.run(app, host=args.host, port=args.port)
        return 0

    parser.print_help()
    return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Convert Metrica tracking data into event data.")
    subparsers = parser.add_subparsers(dest="command")

    generate_parser = subparsers.add_parser("generate", help="Generate events from tracking data.")
    _add_common_generation_args(generate_parser)
    generate_parser.add_argument("--output", required=True, help="Path to the generated CSV file.")

    validate_parser = subparsers.add_parser("validate", help="Validate generated events against the reference file.")
    _add_common_generation_args(validate_parser)
    validate_parser.add_argument(
        "--output",
        help="Optional path to also write the generated CSV during validation.",
    )

    subparsers.add_parser("test", help="Run the automated test suite.")

    serve_parser = subparsers.add_parser("serve", help="Run the frontend and API server.")
    serve_parser.add_argument("--data-dir", required=True, help="Directory containing the sample game data.")
    serve_parser.add_argument("--host", default="127.0.0.1", help="Host interface to bind the web server.")
    serve_parser.add_argument("--port", default=8000, type=int, help="Port to bind the web server.")
    return parser


def _add_common_generation_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--data-dir", required=True, help="Directory containing the sample game data.")
    parser.add_argument("--game-id", required=True, type=int, help="Sample game id to process.")
    parser.add_argument(
        "--format",
        default="metrica",
        choices=["metrica"],
        help="Input format to process.",
    )
    parser.add_argument("--start-frame", type=int, default=None, help="Optional inclusive start frame.")
    parser.add_argument("--end-frame", type=int, default=None, help="Optional inclusive end frame.")
    parser.add_argument("--config", default=None, help="Optional JSON config file overriding detector thresholds.")
