# Chat SFT Packer

Raw chat logs from several vendors are turned into supervised fine-tuning examples. Each
conversation is cleaned up, rendered into a single chat-template string, and trimmed so
it fits the token budget of the source it came from.

The test suite is currently failing. Get it passing by correcting the source code, and be
ready to explain each change: what the symptom was, where it came from, and why.

## Data

- `data/conversations.json`: one object per conversation: `id`, `source`, `tags`
  (a `;`-separated string, may be blank) and `turns` (a list of `{role, content}`).
- `data/roles.csv`: role aliases (`alias` → canonical `role`).
- `data/sources.csv`: one row per source: `max_tokens` (blank = default 64) and
  `include` (`yes`/`y`/`true`/`1`, any case, means included).

## Spec

This spec defines correct behaviour. If the code and the spec disagree, the spec wins.

### Cleaning

- Conversation ids, source names, role names and aliases: trim and lower-case.
- Tags: split on `;`, trim, lower-case. Empty pieces are not tags.
- A role is mapped through `roles.csv` (a role not listed there is kept as-is). Only
  `system`, `user` and `assistant` are usable; turns with any other role are dropped.
- Turn content is trimmed. Turns with blank content are dropped.

### Building an example (per conversation, in file order)

1. A conversation whose source is not in `sources.csv` is rejected as `unknown_source`.
   A conversation whose source is not included is skipped silently (neither kept nor
   rejected).
2. A `system` turn is kept only when it is the first remaining turn. A `system` turn
   anywhere later is dropped, and the turns after it are kept.
3. Consecutive turns with the same role are merged into one turn; contents are joined
   with `\n`.
4. Leading `assistant` turns and trailing `user` turns are dropped. What remains is an
   optional system turn followed by (user, assistant) pairs. With no pairs, the
   conversation is rejected as `no_pair`.
5. Tokens: a turn costs the number of whitespace-separated words in its content plus 4.
   An example's tokens are the sum over its turns.
6. Budget: the source's `max_tokens`. An example **at or under** the budget is kept as
   it is. Otherwise drop the oldest pair, one at a time, until it fits. The system turn
   and the newest pair are never dropped; if it still does not fit, the conversation is
   rejected as `too_long`.
7. Rendering: each kept turn becomes `<|role|>\n` + content + `\n`, followed by a final
   `<|end|>`.

### Output

`chatpack.builder.build_dataset()` returns:

- `examples`: id → `source`, `roles` (the rendered roles in order), `tokens`,
  `dropped_pairs`, `text`.
- `rejected`: id → reason.
- `summary`:
  - `tag_counts`: tag → number of kept examples carrying it;
  - `examples_per_source`: source → number of kept examples;
  - `rejected_by_reason`: reason → count.

## Running

Requires Python 3.10+. No third-party packages.

```bash
python main.py                         # print the dataset
python -m unittest discover -s tests   # run the tests
python -m pytest tests                 # same tests, if you have pytest
```

## Rules

- Do not modify the tests or anything under `data/`.
- Do not modify code marked `# VERIFIED`; it has been reviewed and is correct.
- Everything else is fair game. Each change should be small.
