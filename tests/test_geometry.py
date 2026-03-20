from tracking_to_event.config import DetectorConfig
from tracking_to_event.geometry import classify_out_side, is_ball_out, is_goal_path


def test_ball_out_detection():
    assert is_ball_out((1.02, 0.5))
    assert is_ball_out((0.5, -0.01))
    assert not is_ball_out((0.5, 0.5))


def test_out_side_classification():
    assert classify_out_side((0.5, 1.02)) == "touchline"
    assert classify_out_side((1.01, 0.4)) == "goal_line"
    assert classify_out_side((0.5, 0.5)) is None


def test_goal_path_detection():
    config = DetectorConfig(goal_y_min=0.44, goal_y_max=0.56)
    assert is_goal_path((0.92, 0.5), (1.02, 0.51), config)
    assert not is_goal_path((0.92, 0.7), (1.02, 0.71), config)
