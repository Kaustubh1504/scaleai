# set-097 context questions for an AI assistant

Use these to practise asking an assistant for **context** (what a file or function does,
where a value comes from, what the data looks like) rather than for the fix. The answers
describe what the candidate repo's code does. They don't say whether it is correct.

Interviewers: if the candidate has an assistant, questions like these are fair game.
"What's wrong with this?" or "Fix test 2" is not.

### 1. What happens inside build_report, in order?

It loads contributors, attaches each contributor's latest course results with `rules.attach_courses`, loads projects, runs `assigner.staff`, computes course demand from the projects, and builds the report dict (assignments, open_seats, multi_project, course_demand, top_course).

### 2. How does staff() choose people for one project?

For projects with seats > 0 it filters all contributors with `is_eligible`, sorts them by `rank_key`, and takes the first `seats`. Each pick subtracts `hours_per_seat` from `hours_left`, appends the project id to `contributor.projects`, and adds the contributor id to the project's list.

### 3. What does is_eligible check, and in what order?

Active flag first, then the locale (only if the project has one), then `missing_course(contributor, project.courses)` must be None, and finally `hours_left >= hours_per_seat`.

### 4. Where do contributor.courses values come from?

`attach_courses` calls `latest_results` on every CourseResult row and stores `result` (a lower-cased string such as 'pass' or 'fail') under `contributors[cid].courses[course]`, skipping ids that aren't in contributors.csv.

### 5. How is multi_project built?

From each Contributor object's `projects` list after staffing: contributors sorted by id, kept if `len(c.projects) >= 2`, with the list sorted.

### 6. How does the loader handle a blank rating?

`_number` returns None for a blank cell and a float otherwise. The rating passed to Contributor is then derived from that value and the module-level `DEFAULT_RATING` (3.0).
