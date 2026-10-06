# set-055 context questions for an AI assistant

Use these to practise asking an assistant for **context** (what a file or function does,
where a value comes from, what the data looks like) rather than for the fix. The answers
describe what the candidate repo's code does. They don't say whether it is correct.

Interviewers: if the candidate has an assistant, questions like these are fair game.
"What's wrong with this?" or "Fix test 2" is not.

### 1. How does grade_all pick which attempt to grade?

It calls latest_success(attempts), which keeps, for each (model, item_id), the attempt that passes the status check and has the highest attempt number. grade_all marks an item errored when there is no entry for that pair.

### 2. What does extract_choice return for a timeout output?

For 'Request timed out after 30s' there is no JSON, no answer marker and it isn't a bare letter, so it returns None, which grade_all records as unparsed.

### 3. How are weights read from items.csv?

to_int returns None for a blank cell and an int otherwise. load_items then works out the item's weight from that value and DEFAULT_WEIGHT (1).

### 4. How is the weighted score computed?

For each model: the sum of items[id].weight over correct grades, divided by the sum of weights over all items, rounded to 3 decimals.

### 5. How is category accuracy computed?

For each grade, the item's category gets [hits, count] updated: hits += 1 when the outcome is correct, count += 1 always. Then hits / count, rounded to 3 decimals.

### 6. Are model names normalised?

Yes. load_attempts trims and lower-cases `model` (so 'Bravo' and 'charlie ' become 'bravo' and 'charlie') and upper-cases item ids.
