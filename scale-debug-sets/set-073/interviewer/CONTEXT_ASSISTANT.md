# set-073 context questions for an AI assistant

Use these to practise asking an assistant for **context** (what a file or function does,
where a value comes from, what the data looks like) rather than for the fix. The answers
describe what the candidate repo's code does. They don't say whether it is correct.

Interviewers: if the candidate has an assistant, questions like these are fair game.
"What's wrong with this?" or "Fix test 2" is not.

### 1. What does build_report() call, in order?

load_config, load_contributors, load_projects, then eligibility.current_certs over load_completions. scheduler.staff produces assignments and open_seats, reports.course_table builds the coverage table, and most_demanded picks from it.

### 2. How are project statuses represented after loading?

loader.load_projects converts the cleaned, lower-cased cell with Status(...), so project.status is a models.Status member (Status.OPEN or Status.PAUSED).

### 3. What does current_certs return?

A defaultdict(set) mapping contributor id to the set of course ids for which at least one completion passes is_current(completed_on, as_of, valid_days).

### 4. How does staff() pick each seat?

For each seat it builds a pool of contributors not already on the team for whom is_eligible(...) is true, sorts it with rank_candidates and takes the first, then subtracts hours_per_seat from that contributor's hours_left.

### 5. How does course_table build each row?

A nested stats() helper creates a CourseStats on first sight of a course id. Each current certification adds the contributor id to that course's holders set, and each project requirement may add 1 to demand. The table is returned sorted by course id.

### 6. What does CourseStats.as_dict return?

{'holders': len(self.holders), 'demand': self.demand}.

### 7. How is most_demanded chosen?

min over the CourseStats values by (-demand, course_id), so the highest demand wins and ties go to the lower course id. It returns None for an empty table.
