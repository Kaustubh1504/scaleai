# set-063 context questions for an AI assistant

Use these to practise asking an assistant for **context** (what a file or function does,
where a value comes from, what the data looks like) rather than for the fix. The answers
describe what the candidate repo's code does. They don't say whether it is correct.

Interviewers: if the candidate has an assistant, questions like these are fair game.
"What's wrong with this?" or "Fix test 2" is not.

### 1. What is the flow inside build_dataset()?

It loads the config, the conversation index (conv id → tags) and the grouped turns. For each conversation in index order it applies the `general` default, checks excluded tags, builds the body with `chat.to_messages`, runs `budget.fit_to_budget` with the system message, and stores the example or a rejection reason. The summary is computed from those two dicts at the end.

### 2. What does to_messages do with roles it doesn't know?

It looks each role up in `ROLE_MAP`; a role missing from the map (such as `system` or `tool`) gives None and the turn is skipped, as is a turn with empty text. Consecutive same-role messages are merged with a newline.

### 3. What does fit_to_budget return?

Either None (rejected as too long) or a tuple `(body, dropped)`, where `body` is the remaining non-system messages and `dropped` is a counter increased inside the loop. It loops while `count_tokens([system] + body)` exceeds `max_tokens`.

### 4. Which config keys does load_config read?

It returns a dict with `system_prompt` (stripped), `max_tokens` (as int) and `exclude_tags` (a set of trimmed, lower-cased strings). Other keys in config.json are not returned.

### 5. How are turns ordered inside a conversation?

`load_turns` groups rows by lower-cased conv id and sorts each group by the integer `turn` value, so file order does not matter.

### 6. How is tag_counts built?

A Counter over every tag of every accepted example (rejected conversations are not counted), returned as a dict sorted by tag.
