GAP_FACTOR = 2.5


def duration_s(camera):
    if len(camera) < 2:
        return 0.0
    return (camera[-1] - camera[0]) / 1000


def gap_limit_ms(robot):
    return GAP_FACTOR * 1000 / robot.camera_hz


def has_dropped_frames(camera, robot):
    limit = gap_limit_ms(robot)
    return any(b - a > limit for a, b in zip(camera, camera[1:]))


def duration_ok(seconds, task):
    return task.min_s <= seconds <= task.max_s
