# set-096 context questions for an AI assistant

Use these to practise asking an assistant for **context** (what a file or function does,
where a value comes from, what the data looks like) rather than for the fix. The answers
describe what the candidate repo's code does. They don't say whether it is correct.

Interviewers: if the candidate has an assistant, questions like these are fair game.
"What's wrong with this?" or "Fix test 2" is not.

### 1. What does dataset_report do, step by step?

It loads the dataset's CSV, runs `filters.apply_filters` (blocked source, then incomplete, then low quality), runs `dedupe.dedupe` on what is left, computes targets with `allocator.compute_targets(len(kept), config.fractions)`, then calls `allocator.allocate(kept, targets, config.pins)` and builds the report dict.

### 2. How are a dataset's settings built from datasets.json?

`config.load_datasets` iterates `raw['datasets']` in file order and calls `merge(raw['defaults'], overrides)` for each. `merge` copies the defaults, updates `fractions` key by key, and sets every other key directly. The result is turned into a `DatasetConfig`, with percentages cast to int and pins built as a dict comprehension.

### 3. How does drop_blocked decide a sample is blocked?

It looks up `sample.doc` in the sources registry from `loader.load_sources`. If the doc is missing, or its lower-cased license is in `config.blocked_licenses`, the sample id is recorded as `blocked_source` in the shared `dropped` dict and the sample is removed from the list.

### 4. What does allocate return and in what order are documents placed?

It returns `(assignment, sizes)`: doc id → split (sorted by doc id) and samples per split. Pinned docs present in the data are placed first, in sorted id order; then the rest come from `order_groups`, which sorts by size descending and then doc id, and each goes to `choose_split(sizes, targets)`.

### 5. What does choose_split compute?

A deficit per split, `targets[split] - sizes[split]`, over the `SPLITS` tuple ('train', 'val', 'test'), and returns the result of `max` over SPLITS with a key built from that deficit.

### 6. What is in the duplicates dict and what is kept?

`dedupe` buckets samples by `fingerprint(text)`, picks one per bucket with `pick_original`, and maps every other sample id in the bucket to the chosen id. The kept list preserves the input order of the chosen samples.

### 7. How is label_totals computed?

It builds an `ordered` list from the kept samples and runs `itertools.groupby` over it keyed on `label`, mapping each label to the length of its group in a dict comprehension.
