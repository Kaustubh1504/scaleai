SECOND_UNITS = ("s", "sec", "seconds")


def to_ms(values, unit):
    scale = 1000 if unit in SECOND_UNITS else 1
    return [round(v * scale) for v in values]


# VERIFIED
def drop_repeats(timestamps):
    """Sort and remove repeated timestamps (the logger re-emits a frame when it stalls)."""
    out = []
    for t in sorted(timestamps):
        if out and t == out[-1]:
            continue
        out.append(t)
    return out


def prepare(record, robot):
    """Camera and joint timestamps in ms on the robot's common clock."""
    unit, streams = record["unit"], record["streams"]
    camera_ms = to_ms(streams.get("camera", []), unit)
    joints_ms = to_ms(streams.get("joints", []), unit)
    camera = [t + robot.camera_offset_ms for t in drop_repeats(camera_ms)]
    joints = [t + robot.joint_offset_ms for t in drop_repeats(joints_ms)]
    return camera, joints
