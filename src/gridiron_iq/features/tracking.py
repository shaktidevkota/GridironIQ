"""Tracking-data feature utilities.

These functions are intentionally small and unit-testable. They do not assume
that Big Data Bowl 2027 tracking files use a fixed frame rate; callers should
pass observed timestamps or validated frame intervals.
"""

from __future__ import annotations

import math
from collections.abc import Iterable


def euclidean_distance(x1: float, y1: float, x2: float, y2: float) -> float:
    """Return straight-line distance between two field coordinates."""

    return math.hypot(x2 - x1, y2 - y1)


def path_length(points: Iterable[tuple[float, float]]) -> float:
    """Return total distance traveled through an ordered sequence of points."""

    ordered_points = list(points)
    if len(ordered_points) < 2:
        return 0.0

    return sum(
        euclidean_distance(x1, y1, x2, y2)
        for (x1, y1), (x2, y2) in zip(ordered_points, ordered_points[1:])
    )


def path_efficiency(points: Iterable[tuple[float, float]]) -> float | None:
    """Return displacement divided by path length.

    A value near 1 means the path is close to a straight line. A value near 0
    means the player moved but ended near the starting point. Returns None for
    paths with no movement.
    """

    ordered_points = list(points)
    if len(ordered_points) < 2:
        return None

    total_distance = path_length(ordered_points)
    if total_distance == 0:
        return None

    start_x, start_y = ordered_points[0]
    end_x, end_y = ordered_points[-1]
    displacement = euclidean_distance(start_x, start_y, end_x, end_y)
    return displacement / total_distance


def finite_difference(values: Iterable[float], times: Iterable[float]) -> list[float | None]:
    """Calculate first differences per unit time.

    The first output is None because no previous observation exists. Later
    outputs are None when timestamps are repeated or move backward.
    """

    value_list = list(values)
    time_list = list(times)
    if len(value_list) != len(time_list):
        raise ValueError("values and times must have the same length")
    if not value_list:
        return []

    result: list[float | None] = [None]
    for prev_value, value, prev_time, time in zip(
        value_list, value_list[1:], time_list, time_list[1:]
    ):
        delta_time = time - prev_time
        if delta_time <= 0:
            result.append(None)
        else:
            result.append((value - prev_value) / delta_time)
    return result


def turning_angle_degrees(
    previous_point: tuple[float, float],
    current_point: tuple[float, float],
    next_point: tuple[float, float],
) -> float | None:
    """Return the absolute turn angle at current_point in degrees.

    Returns None when either adjacent segment has zero length.
    """

    ax = previous_point[0] - current_point[0]
    ay = previous_point[1] - current_point[1]
    bx = next_point[0] - current_point[0]
    by = next_point[1] - current_point[1]

    norm_a = math.hypot(ax, ay)
    norm_b = math.hypot(bx, by)
    if norm_a == 0 or norm_b == 0:
        return None

    cosine = ((ax * bx) + (ay * by)) / (norm_a * norm_b)
    bounded_cosine = max(-1.0, min(1.0, cosine))
    return math.degrees(math.acos(bounded_cosine))
