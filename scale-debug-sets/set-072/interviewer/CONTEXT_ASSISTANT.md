# set-072 context questions for an AI assistant

Use these to practise asking an assistant for **context** (what a file or function does,
where a value comes from, what the data looks like) rather than for the fix. The answers
describe what the candidate repo's code does. They don't say whether it is correct.

Interviewers: if the candidate has an assistant, questions like these are fair game.
"What's wrong with this?" or "Fix test 2" is not.

### 1. What is the flow inside build_report()?

load_config, load_speakers and load_clips read the data; filters.usable_clips returns kept clips plus an excluded map; the participating speakers are those with at least one kept clip; stratify.assign_speakers maps each to a split; stats.clips_by_split groups kept clips, and each split gets clips, minutes() and accent_mix().

### 2. Where are consent and held_out parsed?

Both go through normalize.parse_flag, called from loader.load_clips (consent) and loader.load_speakers (held_out).

### 3. How does drop_duplicates decide which clip to keep?

It walks the candidate clips sorted by (recorded_on, id) and keeps the first clip seen for each (speaker_id, normalised transcript) key. Everything else in that key is returned as a duplicate id.

### 4. How are strata built in assign_speakers?

Speakers are sorted by id and appended to a defaultdict(list) keyed by spk.accent. For each accent in sorted order, take_held_out moves held-out speakers out of the pool (they get 'test'), then allocate() splits the remaining pool.

### 5. What does allocate() do with the pool?

It orders the pool with hash_order (sha256 of '<seed>:<id>'), computes n_test and n_val as len(ordered) * percent // 100, and assigns the first n_test to test, the next n_val to val and the rest to train.

### 6. What is in the strata field of the report?

stats.strata_sizes builds a Counter over the accent of every participating speaker (including held-out ones) and returns it as a dict sorted by accent.

### 7. Which clips feed the per-split stats?

Only kept clips. clips_by_split puts each into grouped[assignment[clip.speaker_id]]; minutes() sums duration_ms for the group and accent_mix() counts by speaker accent.
