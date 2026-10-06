from .normalize import norm_transcript


def exclusion_reason(clip, speakers, config):
    """First rule a clip fails, or None if it is usable (before duplicate removal)."""
    if clip.speaker_id not in speakers:
        return "unknown_speaker"
    if not clip.consent:
        return "no_consent"
    if not norm_transcript(clip.transcript):
        return "no_transcript"
    if not config["min_ms"] <= clip.duration_ms < config["max_ms"]:
        return "duration"
    return None


def drop_duplicates(clips):
    """Keep the earliest recording of each (speaker, transcript); return (kept, duplicate ids)."""
    first = {}
    for clip in sorted(clips, key=lambda c: (c.recorded_on, c.id)):
        key = (clip.speaker_id, norm_transcript(clip.transcript))
        first.setdefault(key, clip)
    kept_ids = {c.id for c in first.values()}
    kept = [c for c in clips if c.id in kept_ids]
    dupes = [c.id for c in clips if c.id not in kept_ids]
    return kept, dupes


def usable_clips(clips, speakers, config):
    excluded, candidates = {}, []
    for clip in clips:
        reason = exclusion_reason(clip, speakers, config)
        if reason:
            excluded[clip.id] = reason
        else:
            candidates.append(clip)
    kept, dupes = drop_duplicates(candidates)
    for cid in dupes:
        excluded[cid] = "duplicate"
    return kept, excluded
