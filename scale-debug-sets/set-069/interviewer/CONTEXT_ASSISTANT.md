# set-069 context questions for an AI assistant

Use these to practise asking an assistant for **context** (what a file or function does,
where a value comes from, what the data looks like) rather than for the fix. The answers
describe what the candidate repo's code does. They don't say whether it is correct.

Interviewers: if the candidate has an assistant, questions like these are fair game.
"What's wrong with this?" or "Fix test 2" is not.

### 1. What does build_report() do?

It creates a GuidelineOrigin from guidelines.json and a GuidelineService with config.json, then replays load_trace(trace.csv) in ts order through service.lookup, recording each outcome, the version and locale served, and the labels.

### 2. Walk me through GuidelineService.lookup.

It builds a cache key, calls cache.get(key, ts). On None it calls origin.fetch; if that is also None it returns ('not_found', None) without caching. Otherwise it puts the value with the project's TTL and marks a miss. Finally it extends value['labels'] with the client's overrides for the project and returns (outcome, value).

### 3. How does TTLCache decide whether an entry is fresh?

Each Entry stores stored_at and ttl_s; expires_at is their sum. get compares now with expires_at; an expired entry is deleted and get returns None.

### 4. What does put store?

An Entry holding copy.deepcopy(value), the current time and the TTL, under the given key, replacing anything already there.

### 5. How are timestamps turned into numbers?

origin.parse_time tries four formats and returns datetime.timestamp() (seconds as a float, local time). Both the trace and published_at use it, so they are on the same clock.

### 6. Which clients have overrides?

config.json: acme gets 'sarcasm' on sentiment, and globex gets 'occluded' on pose (pose is not in the origin, so that request is not_found).
