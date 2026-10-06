import hashlib


def stable_key(seed, speaker_id):
    return hashlib.sha256(f"{seed}:{speaker_id}".encode("utf-8")).hexdigest()


# VERIFIED
def hash_order(speakers, seed):
    return sorted(speakers, key=lambda s: stable_key(seed, s.id))
