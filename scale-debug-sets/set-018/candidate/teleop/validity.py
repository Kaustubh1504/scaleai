def check_episode(episode, metrics, robot, thresholds):
    """Every rule the episode breaks, in a fixed order. Empty means valid."""
    reasons = []
    if robot is None:
        reasons.append("unknown_robot")
    elif not robot.active:
        reasons.append("robot_inactive")
    if metrics.duration_s < thresholds.min_duration_s:
        reasons.append("too_short")
    if robot is not None and metrics.max_gap_ms >= robot.max_gap_ms:
        reasons.append("frame_gap")
    if metrics.sync_rate < thresholds.min_sync_rate:
        reasons.append("unsynced")
    return reasons
