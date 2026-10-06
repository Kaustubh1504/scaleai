# set-058 context questions for an AI assistant

Use these to practise asking an assistant for **context** (what a file or function does,
where a value comes from, what the data looks like) rather than for the fix. The answers
describe what the candidate repo's code does. They don't say whether it is correct.

Interviewers: if the candidate has an assistant, questions like these are fair game.
"What's wrong with this?" or "Fix test 2" is not.

### 1. What does build_report do, in order?

Loads plans, tenants, credits and events (events only for known active tenants), groups events by tenant, then for each active tenant (sorted) calls apply_limit with limit_for's result and builds an invoice from the allowed events. The statement is built from all loaded events and the invoices.

### 2. What does limit_for return?

The tenant's rpm_override if it isn't None; otherwise None for the plan checked in its second `if`; otherwise plans[tenant.plan].rpm. None means apply_limit allows everything.

### 3. How does apply_limit maintain its window?

It sorts the tenant's events by ts and keeps a deque of timestamps of allowed requests. Before each event it pops timestamps from the left while the condition in its while-loop holds, then allows the event if limit is None or the deque is shorter than limit. Only allowed requests are appended.

### 4. What type is Tenant.plan and how is it parsed?

It is a `Plan` member (a plain `Enum` with values 'free', 'pro', 'enterprise'), built with `Plan(norm_id(row['plan']))` in load_tenants. Invoices output `tenant.plan.value`.

### 5. How are timestamps parsed?

`parse_ts` treats an all-digit string as epoch seconds via fromtimestamp(..., tz=UTC), otherwise tries '%Y-%m-%dT%H:%M:%SZ' then '%Y-%m-%d %H:%M:%S' and attaches UTC.

### 6. How is a tenant's credit looked up?

load_credits builds a dict from credits.json, transforming each key in its comprehension; build_report then calls credits.get(tenant_id, 0) with the normalised tenant id.

### 7. What does top_tenants count?

A Counter of tenant_id over every loaded event, so allowed and throttled requests both count, but ignored events (unknown or inactive tenants) don't. It is sorted with a key over the count and tenant id and sliced to TOP_N = 3.
