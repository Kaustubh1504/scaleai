from collections import Counter

SPLITS = ("train", "val", "test")


def clips_by_split(clips, assignment):
    grouped = {name: [] for name in SPLITS}
    for clip in clips:
        grouped[assignment[clip.speaker_id]].append(clip)
    return grouped


def accent_mix(clips, speakers):
    mix = Counter()
    for clip in clips:
        mix[speakers[clip.speaker_id].accent] += 1
    return dict(sorted(mix.items()))


def strata_sizes(active_speakers):
    return dict(sorted(Counter(s.accent for s in active_speakers).items()))
