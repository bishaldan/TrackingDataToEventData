from __future__ import annotations

import math

from tracking_to_event.config import DetectorConfig


def distance(p1: tuple[float, float], p2: tuple[float, float]) -> float:
    return math.hypot(p1[0] - p2[0], p1[1] - p2[1])


def is_ball_out(ball: tuple[float, float], tolerance: float = 0.0) -> bool:
    x, y = ball
    return x < 0.0 - tolerance or x > 1.0 + tolerance or y < 0.0 - tolerance or y > 1.0 + tolerance


def classify_out_side(ball: tuple[float, float], tolerance: float = 0.0) -> str | None:
    x, y = ball
    if y < 0.0 - tolerance or y > 1.0 + tolerance:
        return "touchline"
    if x < 0.0 - tolerance or x > 1.0 + tolerance:
        return "goal_line"
    return None


def is_corner_exit(ball: tuple[float, float], tolerance: float = 0.08) -> bool:
    x, y = ball
    return (x <= 0.0 and y <= tolerance) or (x <= 0.0 and y >= 1.0 - tolerance) or (x >= 1.0 and y <= tolerance) or (x >= 1.0 and y >= 1.0 - tolerance)


def y_at_goal_line(start_xy: tuple[float, float], end_xy: tuple[float, float]) -> float | None:
    x1, y1 = start_xy
    x2, y2 = end_xy
    dx = x2 - x1
    dy = y2 - y1
    if dx == 0:
        return None

    goal_x = 1.0 if dx > 0 else 0.0
    t = (goal_x - x1) / dx
    if t < 0:
        return None
    return y1 + t * dy


def is_goal_path(start_xy: tuple[float, float], end_xy: tuple[float, float], config: DetectorConfig) -> bool:
    if classify_out_side(end_xy, config.ball_out_tolerance) != "goal_line":
        return False

    y_value = y_at_goal_line(start_xy, end_xy)
    if y_value is None:
        return False

    return config.goal_y_min <= y_value <= config.goal_y_max
