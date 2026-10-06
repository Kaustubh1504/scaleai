from collections import defaultdict
from dataclasses import dataclass

MIN_VOTES = 2


@dataclass(frozen=True)
class Entity:
    start: int
    end: int
    label: str
    votes: int

    @property
    def length(self):
        return self.end - self.start


def candidates(spans):
    """doc_id -> entities with at least MIN_VOTES distinct annotators, in offset order."""
    voters = defaultdict(set)
    for s in spans:
        voters[(s.doc_id, s.start, s.end, s.label)].add(s.annotator)
    by_doc = defaultdict(list)
    for (doc_id, start, end, label), who in sorted(voters.items()):
        if len(who) >= MIN_VOTES:
            by_doc[doc_id].append(Entity(start, end, label, len(who)))
    return by_doc


def _overlaps(a, b):
    return a.start < b.end and b.start < a.end


def resolve_doc(entities):
    """Greedy: strongest first; drop anything overlapping an entity already kept."""
    kept = []
    for ent in sorted(entities, key=lambda e: (-e.votes, -e.length, e.start)):
        if not any(_overlaps(ent, k) for k in kept):
            kept.append(ent)
    return sorted(kept, key=lambda e: e.start)
