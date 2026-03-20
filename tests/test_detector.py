from tracking_to_event.config import DetectorConfig
from tracking_to_event.detector import detect_segments
from tracking_to_event.models import BallPosition, FrameRecord, PlayerPosition


def _frame(frame: int, ball_xy: tuple[float, float], players: list[PlayerPosition]) -> FrameRecord:
    return FrameRecord(period=1, frame=frame, time_seconds=frame / 25.0, ball=BallPosition(*ball_xy), players=players)


def test_detect_segments_handles_pass_after_ball_flight():
    frames = [
        _frame(1, (0.50, 0.50), [PlayerPosition("Home", "1", 0.50, 0.50), PlayerPosition("Home", "2", 0.60, 0.60)]),
        _frame(2, (0.52, 0.50), [PlayerPosition("Home", "1", 0.52, 0.50), PlayerPosition("Home", "2", 0.60, 0.60)]),
        _frame(3, (0.56, 0.52), [PlayerPosition("Home", "1", 0.50, 0.50), PlayerPosition("Home", "2", 0.61, 0.60)]),
        _frame(4, (0.60, 0.60), [PlayerPosition("Home", "1", 0.50, 0.50), PlayerPosition("Home", "2", 0.60, 0.60)]),
    ]

    segments = detect_segments(
        frames,
        DetectorConfig(
            control_radius=0.03,
            sticky_radius=0.035,
            competing_radius=0.05,
            switch_confirmation_frames=1,
        ),
    )

    assert len(segments) == 2
    first, second = segments
    assert first.player_label == "Player1"
    assert second.player_label == "Player2"
    assert first.end_frame == 2
    assert second.start_frame == 4


def test_detect_segments_creates_ball_out_segment():
    frames = [
        _frame(1, (0.50, 0.50), [PlayerPosition("Home", "1", 0.50, 0.50)]),
        _frame(2, (1.02, 0.50), [PlayerPosition("Home", "1", 0.90, 0.50)]),
        _frame(3, (1.04, 0.50), [PlayerPosition("Home", "1", 0.90, 0.50)]),
        _frame(4, (0.50, 0.50), [PlayerPosition("Away", "2", 0.50, 0.50)]),
    ]

    segments = detect_segments(frames, DetectorConfig())

    assert len(segments) == 3
    assert segments[1].start_frame == 2
    assert segments[1].end_frame == 3
