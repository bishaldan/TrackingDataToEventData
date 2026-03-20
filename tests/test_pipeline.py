from tracking_to_event.config import DetectorConfig
from tracking_to_event.pipeline import build_events_from_segments, generate_dataframe_for_game
from tracking_to_event.models import BallOutSegment, PossessionSegment
from tracking_to_event.validation import validate_game


def test_build_events_from_segments_generates_pass_restart_and_shot():
    config = DetectorConfig()
    segments = [
        PossessionSegment(1, "Away", "Player19", 1, 0.04, (0.45, 0.39), 1, 0.04, (0.45, 0.39)),
        PossessionSegment(1, "Away", "Player21", 3, 0.12, (0.55, 0.43), 3, 0.12, (0.55, 0.43)),
        BallOutSegment(1, 4, 0.16, (1.01, 0.50), 5, 0.20, (1.02, 0.51)),
        PossessionSegment(1, "Home", "Player1", 10, 0.40, (0.50, 0.50), 10, 0.40, (0.50, 0.50)),
    ]

    events = build_events_from_segments(segments, config)
    event_types = [event.event_type for event in events]

    assert event_types == ["SET PIECE", "PASS", "SHOT", "SET PIECE"]
    assert events[0].subtype == "KICK OFF"
    assert events[-1].subtype == "KICK OFF"


def test_generate_dataframe_for_sample_game_subset():
    df = generate_dataframe_for_game(
        data_dir="data",
        game_id=1,
        input_format="metrica",
        start_frame=1,
        end_frame=2500,
    )

    assert not df.empty
    assert set(["Type", "Team", "Start Frame", "End Frame"]).issubset(df.columns)
    assert {"SET PIECE", "PASS"}.issubset(set(df["Type"]))


def test_validate_game_returns_report():
    report = validate_game(
        data_dir="data",
        game_id=1,
        input_format="metrica",
        start_frame=1,
        end_frame=2500,
    )

    assert report.generated_event_count > 0
    assert report.supported_reference_count > 0
    assert report.type_counts
