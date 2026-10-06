# set-039 context questions for an AI assistant

Use these to practise asking an assistant for **context** (what a file or function does,
where a value comes from, what the data looks like) rather than for the fix. The answers
describe what the candidate repo's code does. They don't say whether it is correct.

Interviewers: if the candidate has an assistant, questions like these are fair game.
"What's wrong with this?" or "Fix test 2" is not.

### 1. What does build_examples do for each conversation?

It runs loader.validate on the cleaned messages (rejecting with its reason), adds the default system prompt with with_system, trims with render.truncate, and stores text, tokens, spans and turns_dropped for the trimmed messages. A None from truncate becomes a too_long rejection.

### 2. How are roles represented?

models.Role is an Enum with values 'system', 'user', 'assistant'. normalize_role lower-cases and trims the raw string, maps aliases through ALIASES, and returns Role(name).

### 3. How does truncate decide what to drop?

It works on `kept`, starting after the system message, and deletes kept[start:start + 2] while the messages don't fit and more than one pair remains. It returns kept if it fits, otherwise None.

### 4. How are tokens counted?

render.count_tokens returns len(content.split()) + 2 per message; total_tokens sums that over the list.

### 5. What does a rendered block look like?

render.block(m) returns tag(m) + '\n' + content + '<|end|>\n', where tag(m) is '<|' + role value + '|>'. render() concatenates the blocks.

### 6. Which conversations get trimmed with this data?

c07 (54 tokens before trimming) and c13 (46) are over the 40-token budget and lose their first user/assistant pair. c12 has a single long pair and cannot be trimmed.
