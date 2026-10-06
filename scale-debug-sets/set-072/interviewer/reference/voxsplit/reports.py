from pathlib import Path

from .filters import usable_clips
from .loader import load_clips, load_config, load_speakers
from .stats import accent_mix, clips_by_split, strata_sizes
from .stratify import assign_speakers

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def minutes(clips):
    total_ms = sum(c.duration_ms for c in clips)
    return round(total_ms / 60_000, 2)


def build_report(data_dir=None):
    data_dir = Path(data_dir or DATA_DIR)
    config = load_config(data_dir / "config.json")
    speakers = load_speakers(data_dir / "speakers.csv")
    clips = load_clips(data_dir / "clips.csv")

    kept, excluded = usable_clips(clips, speakers, config)
    active = [speakers[sid] for sid in sorted({c.speaker_id for c in kept})]
    assignment = assign_speakers(active, config)
    grouped = clips_by_split(kept, assignment)

    return {
        "excluded": dict(sorted(excluded.items())),
        "strata": strata_sizes(active),
        "assignment": dict(sorted(assignment.items())),
        "splits": {
            name: {
                "clips": sorted(c.id for c in group),
                "minutes": minutes(group),
                "accents": accent_mix(group, speakers),
            }
            for name, group in grouped.items()
        },
    }
