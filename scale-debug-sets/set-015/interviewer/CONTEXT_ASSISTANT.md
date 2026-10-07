# set-015 context questions for an AI assistant

Use these to practise asking an assistant for **context** (what a file or function does,
where a value comes from, what the data looks like) rather than for the fix. The answers
describe what the candidate repo's code does. They don't say whether it is correct.

Interviewers: if the candidate has an assistant, questions like these are fair game.
"What's wrong with this?" or "Fix test 2" is not.

### 1. What does build_example() do to one conversation?

It calls `normalise_roles` (lower-case, alias, reject unknown roles or empty content), then `merge_consecutive`, then `check_order`, and finally returns the result of `truncate`, which is `(messages, dropped_pairs)`. Any rule failure raises `Rejected` with the reason as its message.

### 2. What does clean_content return?

It is in loader.py and turns the raw `content` value of a message into the string stored on `Message.content`. Its result is what normalise_roles later tests for emptiness.

### 3. How does check_order handle the system message?

If the first message is `system`, it is skipped. Any other `system` message raises `misplaced_system`. The rest must alternate user/assistant starting with user, and the last must be assistant, otherwise `bad_order`.

### 4. How are tokens counted?

`count_tokens` sums `len(content.split()) + overhead` over the messages, with overhead taken from `per_message_overhead` in config.json (4).

### 5. Where is the template text produced, and is it used for token counting?

`render.render` builds the text from a list of parts and joins it. The token count in the report comes from `count_tokens` on the messages, not from the rendered text.

### 6. Which conversations does the summary look at?

`sources` and `tag_counts` are computed over every conversation loaded from the file, kept or rejected. `longest_example` looks only at the kept examples.
