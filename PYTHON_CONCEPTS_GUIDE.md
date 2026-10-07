# Python & Backend Concepts Guide

A study guide for the code in `scale-debug-sets/` and `scale-backend-sets/`.
Every feature here actually appears in those repos. Examples are generic so they
don't give away any set's answers.

**How to use this:** read Part 1 once from top to bottom. When a line of code
confuses you, search this file (Cmd+F) for the keyword, e.g. `lambda`,
`default_factory`, `setdefault`, `async`.

- **Part 1:** Python syntax (both rounds)
- **Part 2:** Debugging-round concepts and the common bug patterns
- **Part 3:** Backend-round concepts (HTTP, FastAPI, LLM calls, retries, concurrency)
- **Part 4:** Cheat sheets

---

# PART 1: PYTHON SYNTAX

## 1.1 How a project is laid out: modules, packages, imports

```
set-001/candidate/
├── main.py              <- entry point you run
├── staffing/            <- a "package" (a folder of .py files)
│   ├── __init__.py      <- marks the folder as a package (often empty)
│   ├── models.py        <- each .py file is a "module"
│   ├── loader.py
│   └── rules.py
└── tests/
    └── test_1_assignment.py
```

```python
import json                              # import a whole module, then use json.dumps(...)
from pathlib import Path                 # import one name out of a module
from staffing.reports import build_report   # absolute import: package.module
from .models import Contributor          # relative import: "." means "this same package"
from .rules import is_eligible, rank_candidates   # several names at once
```

- `from .models import X` only works inside a package. That's why you run
  things from the `candidate/` folder (`python main.py`, `python -m pytest`).
- `python -m pytest` and `python -m mock_services.llm_server` mean "run this
  module as a script". This puts the current folder on the import path, which
  is why imports like `from app.main import create_app` work.

### `if __name__ == "__main__":`

```python
if __name__ == "__main__":
    print(json.dumps(build_report(), indent=2))
```

The code under this line runs **only** when you run the file directly
(`python main.py`). It does **not** run when another file imports it. Test files
end with `unittest.main()` under this guard so you can run them directly too.

### `from __future__ import annotations`

Seen at the top of many backend files. It makes type hints lazy: Python stores
them as strings and doesn't evaluate them. You can ignore it. It has no effect
on how the code runs.

### Docstrings and comments

```python
"""Triple-quoted string at the top of a file/function = documentation (docstring)."""
# A hash starts a comment.
# VERIFIED   <- in the debug sets, this marks code you must not change.
#              Some VERIFIED code looks suspicious on purpose (a red herring).
```

**Warning:** in the debug round, comments can be misleading on purpose.
`# most important first` above a sort doesn't prove the sort does that.
**Trust the README spec and the data, not the comments.**

---

## 1.2 Variables, basic types, truthiness

```python
count = 3            # int
rating = 4.5         # float
name = "Ana"         # str
active = True        # bool (True / False, capitalised)
nothing = None       # None = "no value" (like null)
```

### Truthiness: what counts as False

These are all **falsy** (treated as False in `if` and `or`):

```
False   None   0   0.0   ""   []   {}   set()   ()
```

Everything else is **truthy**, including `"0"`, `"false"`, `" "`, and `[0]`.

```python
if items:          # means: if items is not empty
if not name:       # means: if name is "" or None
```

### The `x or default` idiom, and the falsy-zero trap

```python
path = path or DATA_DIR / "contributors.csv"   # use path if given, else the default
value = (value or "").strip()                  # turn None into "" before calling .strip()
```

`a or b` returns `a` if `a` is truthy, otherwise `b`. That's handy, but it's
**a classic bug** when `0` is a real value:

```python
headcount = row_headcount or 5      # BUG if headcount 0 is valid: 0 -> 5
timeout   = config.timeout or 10    # BUG: timeout=0 silently becomes 10

# Correct when 0 (or "") is meaningful:
headcount = row_headcount if row_headcount is not None else 5
```

### `is None` vs `== None`, `is` vs `==`

```python
if x is None:      # correct way to check for None
if x == 5:         # compare values
```

### `bool("false")` is True

```python
bool("false")   # True!  any non-empty string is truthy
bool("")        # False

# Correct way to parse yes/no text:
TRUTHY = {"y", "yes", "true", "1"}
available = text.strip().lower() in TRUTHY
```

### Converting types

```python
int("42")        # 42
int(" 42 ")      # 42 (int() tolerates surrounding whitespace)
int("4.0")       # ValueError!
float("4.5")     # 4.5
str(42)          # "42"
int(4.9)         # 4  (truncates, does NOT round)
round(2.5)       # 2  (banker's rounding: .5 rounds to the even number)
round(3.14159, 2)  # 3.14
```

### Integer and float division

```python
7 / 2     # 3.5   (always a float)
7 // 2    # 3     (floor division)
-7 // 2   # -4    (floors toward minus infinity)
7 % 2     # 1     (remainder)
2 ** 3    # 8     (power)
0.1 + 0.2 == 0.3   # False! floats are approximate; use round() or Decimal for money
```

---

## 1.3 Strings

```python
s = "  Hello World  "
s.strip()          # "Hello World"   remove whitespace at both ends
s.lstrip() / s.rstrip()
s.lower()          # "  hello world  "
s.upper()
s.replace("o", "0")
s.startswith("  He")   # True
s.endswith(".csv")
"a,b,c".split(",")     # ["a", "b", "c"]
"a b  c".split()       # ["a", "b", "c"]  no argument = split on any whitespace, drop empties
";".join(["a", "b"])   # "a;b"
"abc"[0]   "abc"[-1]   "abc"[1:]      # "a"  "c"  "bc"
"py" in "python"       # True (substring check)
len("abc")             # 3
```

### The `"".split(",")` trap

```python
"".split(";")          # [""]  a list with ONE empty string, NOT []
"a;;b".split(";")      # ["a", "", "b"]
" a ; b ".split(";")   # [" a ", " b "]  pieces keep their spaces

# Safe pattern (used in the loaders):
parts = [p.strip() for p in text.split(";") if p.strip()]
```

### Normalising IDs

Data files are messy on purpose: `"c02 "`, `" C06"`, `"P07"`, `"p07"`. If one
place does `.strip().upper()` and another place doesn't, lookups silently fail.

```python
cid = raw.strip().upper()
```

**Rule:** every place that **creates** an ID and every place that **compares**
one must normalise it the same way.

### f-strings (formatted strings)

```python
name, n = "Ana", 3
f"{name} has {n} tasks"          # "Ana has 3 tasks"
f"{n * 2}"                       # expressions allowed: "6"
f"{value!r}"                     # !r = repr(): shows quotes, e.g. 'abc' or None
f"{3.14159:.2f}"                 # "3.14"   format spec after the colon
f"{42:05d}"                      # "00042"
```

`!r` is great for debugging: `print(f"{x!r}")` shows `'C01 '` with its quotes, so
stray spaces become visible.

### `.format()` and escaping braces

```python
PROMPT = 'Labels: {labels}. Reply as {{"label": "..."}}'
PROMPT.format(labels="a, b")     # 'Labels: a, b. Reply as {"label": "..."}'
```

`{{` and `}}` produce a literal `{` and `}`. This matters when a prompt template
contains JSON.

### Multi-line strings

```python
text = """line one
line two"""
```

---

## 1.4 Collections: list, tuple, dict, set

### list: ordered, changeable

```python
xs = [3, 1, 2]
xs.append(4)          # [3, 1, 2, 4]
xs.extend([5, 6])
xs[0]                 # 3
xs[-1]                # 6 (last item)
len(xs)
3 in xs               # True (slow for big lists: checks one by one)
xs.sort()             # sorts IN PLACE, returns None
ys = sorted(xs)       # returns a NEW sorted list
xs.pop()              # remove and return the last item
xs.pop(0)             # remove and return the first item
```

### tuple: ordered, NOT changeable

```python
point = (3, 4)
x, y = point          # "unpacking"
a, b = b, a           # swap
DATE_FORMATS = ("%Y-%m-%d", "%m/%d/%Y")   # often used for constants
```

### dict: key -> value mapping

```python
d = {"P01": 2, "P02": 0}
d["P01"]              # 2
d["P99"]              # KeyError!
d.get("P99")          # None (no error)
d.get("P99", 0)       # 0   (default)
d["P03"] = 5          # add/overwrite
"P01" in d            # True (checks KEYS)
del d["P01"]
d.keys()   d.values()   d.items()
for key, value in d.items():
    ...
len(d)
```

**`d.get(k, default)` and the falsy trap:** `d.get(k) or 5` replaces a stored 0
with 5. Use `d.get(k, 5)` if you only want the default when the key is missing.

**`setdefault`** returns the existing value, or inserts the default first:

```python
groups = {}
groups.setdefault("A", []).append(1)    # {"A": [1]}
groups.setdefault("A", []).append(2)    # {"A": [1, 2]}
```

**Merging and copying dicts:**

```python
merged = {**a, **b}                 # b's values win on conflicts
doc = {**summary, "tickets": rows}  # copy summary and add one key
copy = dict(d)                      # shallow copy
```

**Sorting a dict by key** (dicts remember insertion order):

```python
dict(sorted(d.items()))                       # sorted by key
dict(sorted(d.items(), key=lambda kv: kv[1])) # sorted by value
```

### set: unordered, unique items, fast `in`

```python
taken = set()           # NOT {} (that's an empty dict!)
taken.add("C01")
taken.update(["C02", "C03"])
"C01" in taken          # very fast
a | b    # union        a & b   # intersection
a - b    # difference   a <= b  # is a a subset of b?
skills = {"python", "sql"}
```

### Nested data (what JSON looks like in Python)

```python
report = {
    "assignments": {"P01": ["C01", "C15"]},
    "bench": ["C08"],
}
report["assignments"]["P01"][0]    # "C01"
```

---

## 1.5 Loops and control flow

```python
for item in items:
    if bad(item):
        continue        # skip to the next item
    if done(item):
        break           # leave the loop entirely
    process(item)

for i in range(5):          # 0,1,2,3,4   (stops BEFORE 5)
for i in range(1, 6):       # 1..5
for i in range(10, 0, -1):  # 10..1

for i, row in enumerate(rows):            # i = 0, 1, 2, ...
for i, row in enumerate(rows, start=1):   # i = 1, 2, 3, ...  (1-based row numbers)

for name, score in zip(names, scores):    # walk two lists together
                                          # (stops at the SHORTER one)

while queue:
    item = queue.pop(0)
```

### Conditional expression (one-line if/else)

```python
status = "failed" if error else "classified"
```

### Chained comparisons

```python
0 <= confidence <= 1     # same as (0 <= confidence) and (confidence <= 1)
```

### Off-by-one checklist

| Question | Watch for |
|---|---|
| "at most N" / "up to N" | `<=` vs `<` |
| "expires at time T": is it expired AT T? | `now >= expires_at` vs `now > expires_at` (the spec decides) |
| `range(n)` | gives 0..n-1 |
| `xs[:n]` | first n items (indexes 0..n-1) |
| `xs[a:b]` | includes a, **excludes** b |
| 1-based vs 0-based row numbers | `enumerate(rows, start=1)` |

### Slicing

```python
xs = [10, 20, 30, 40, 50]
xs[:2]     # [10, 20]       first 2
xs[2:]     # [30, 40, 50]   from index 2
xs[-2:]    # [40, 50]       last 2
xs[1:3]    # [20, 30]
xs[::-1]   # reversed copy
xs[:100]   # whole list, no error if too long
```

---

## 1.6 Comprehensions (very common in this code)

A comprehension builds a collection in one line. Read it as English: **"make a
list of `X` for each `item` in `items` if `condition`"**.

```python
# list comprehension
ids = [c.id for c in contributors]
pool = [c for c in contributors if c.id not in taken and is_eligible(c, project)]

# set comprehension (curly braces, single value)
skills = {s.lower() for s in parts}

# dict comprehension (curly braces, key: value)
by_id = {c.id: c for c in contributors}
fresh = {r["ticket_id"]: r for r in results}
```

The plain-loop version of `pool = [...]` above:

```python
pool = []
for c in contributors:
    if c.id not in taken and is_eligible(c, project):
        pool.append(c)
```

### Nested comprehension (two `for`s)

```python
staffed = {cid for ids in assignments.values() for cid in ids}
```

Read the `for`s left to right, like nested loops:

```python
staffed = set()
for ids in assignments.values():
    for cid in ids:
        staffed.add(cid)
```

### Generator expressions inside sum / any / all / max / min

```python
total = sum(t.amount for t in tasks)
classified = sum(r["status"] == "classified" for r in results)   # counts the Trues (True == 1)
has_bad = any(r.error for r in rows)    # True if at least one is truthy
all_ok  = all(r.ok for r in rows)       # True if every one is truthy (and True for an EMPTY list!)
best = max(scores, key=lambda s: s.value)
max([])            # ValueError! use max(xs, default=0)
```

### Dict/set comprehension variables are fresh

Each comprehension creates new objects. A common bug is building the right
collection and then using the old variable afterwards.

---

## 1.7 Functions

```python
def assign(contributors, projects):
    ...
    return assignments          # no return statement -> returns None
```

### Default arguments and keyword arguments

```python
def load(path=None, strict=False):
    path = path or DEFAULT_PATH

load()                          # both defaults
load("x.csv")                   # positional
load(strict=True)               # keyword: skip path, set strict
```

### The mutable default trap

```python
def add(item, bucket=[]):   # BUG: the SAME list is reused on every call
    bucket.append(item)
    return bucket

def add(item, bucket=None): # correct
    bucket = [] if bucket is None else bucket
```

(This is the same reason dataclasses need `field(default_factory=list)`, see 1.9.)

### Keyword-only arguments: the bare `*`

```python
def _result(ticket_id, attempts, *, label=None, error=None):
    ...
_result("T1", 2, label="bug")    # OK
_result("T1", 2, "bug")          # TypeError: label must be passed by name
```

### `*args` and `**kwargs`

```python
def log(*args, **kwargs):
    # args   = tuple of extra positional arguments
    # kwargs = dict of extra keyword arguments
    print(args, kwargs)

log(1, 2, x=3)    # (1, 2) {'x': 3}

# Unpacking when CALLING:
nums = [1, 2, 3];  f(*nums)        # same as f(1, 2, 3)
opts = {"x": 1};   f(**opts)       # same as f(x=1)
```

### Returning several values

```python
def parse(text):
    return label, confidence      # really returns a tuple

label, conf = parse(text)
```

### lambda: a tiny one-line function

```python
key = lambda p: (p.priority, p.id)
# is the same as
def key(p):
    return (p.priority, p.id)
```

Lambdas show up mostly as `key=` arguments to `sorted`, `max`, and `min`.

### Functions are values; passing them in (dependency injection)

```python
async def send_with_retries(do_request, policy, sleep=asyncio.sleep):
    ...
    await sleep(delay)
```

`sleep` is a parameter so tests can pass a fake that returns instantly and
records the delays. The same idea is behind `create_app(storage_dir, llm, clock)`
in the backend sets: **pass dependencies in so tests can swap in fakes.**

### Closures: functions defined inside functions

```python
def create_app(storage_dir):
    store = Store(storage_dir)

    @app.get("/uploads/{upload_id}")
    def get_upload(upload_id):
        return store.load(upload_id)   # inner function can use outer variables
    return app
```

### Type hints

Type hints are **documentation only**. Python does not enforce them at runtime
(FastAPI and Pydantic do read them, see Part 3).

```python
def make_llm(config: LLMConfig | None = None) -> MockLLMClient: ...
#                    ^^^^^^^^^^^^^^^^^^^^ "LLMConfig or None"   ^^ return type

skills: set[str]              # a set of strings
rows: list[dict]              # a list of dicts
counts: dict[str, int]
pair: tuple[str, float]
```

### Decorators: the `@something` line above a function

```python
@app.get("/health")
def health():
    return {"status": "ok"}
```

A decorator wraps or registers the function below it. `@app.get("/health")`
means "register `health` as the handler for GET /health". Others you'll see:
`@dataclass`, `@property`, `@classmethod`, `@staticmethod`.

---

## 1.8 Classes and objects

```python
class Account:
    fee = 0.5                          # class attribute (shared by all instances)

    def __init__(self, owner, balance=0):   # constructor, runs on Account(...)
        self.owner = owner             # instance attributes
        self.balance = balance

    def deposit(self, amount):         # method; `self` is the object itself
        self.balance += amount
        return self.balance

acct = Account("Ana", 10)              # self is passed automatically
acct.deposit(5)                        # 15
acct.owner                             # "Ana"
```

### `@property`: a method that reads like an attribute

```python
class Lease:
    def __init__(self, start, ttl):
        self.start, self.ttl = start, ttl

    @property
    def expires_at(self):
        return self.start + self.ttl

lease.expires_at       # no parentheses
```

### `@classmethod` and `@staticmethod`

```python
class Config:
    @classmethod
    def from_dict(cls, d):        # gets the CLASS as `cls`; often an alternate constructor
        return cls(**d)

    @staticmethod
    def helper(x):                # gets neither self nor cls; just a function in the class
        return x * 2
```

In tests, `@classmethod def setUpClass(cls)` runs **once** before all tests in
the class (see 1.15).

### Inheritance and `super()`

```python
class LLMError(Exception):
    retryable = False

class LLMRateLimitError(LLMError):     # IS-A LLMError
    retryable = True
    def __init__(self, message, retry_after):
        super().__init__(message)      # run the parent's __init__
        self.retry_after = retry_after
```

`except LLMError:` also catches `LLMRateLimitError`, because it's a subclass.

### Special ("dunder") methods

`__init__` (constructor), `__repr__` (how the object prints for debugging),
`__eq__` (`==`), `__lt__` (`<`, used by sorting), `__len__`, `__contains__` (`in`).

---

## 1.9 dataclasses (used in almost every set)

A dataclass is a class that mainly holds data. Python writes `__init__`,
`__repr__`, and `__eq__` for you.

```python
from dataclasses import dataclass, field
from datetime import date

@dataclass
class Contributor:
    id: str                                         # required (no default)
    name: str
    skills: set[str] = field(default_factory=set)   # each object gets its OWN new set
    rating: float = 0.0                             # simple default
    joined: date | None = None
    available: bool = True

c = Contributor(id="C01", name="Ana", rating=4.8)
c.rating            # 4.8
print(c)            # Contributor(id='C01', name='Ana', skills=set(), rating=4.8, ...)
c == Contributor(id="C01", name="Ana", rating=4.8)   # True (compares fields)
```

- Fields **without** defaults must come before fields **with** defaults.
- **`field(default_factory=set)`**: you can't write `skills: set = set()`,
  because one set would be shared by every object. `default_factory` calls
  `set()` again for each new object. Same for `list` and `dict`.

### `@dataclass(frozen=True)`: immutable

```python
@dataclass(frozen=True)
class Task:
    id: str
    priority: int

t = Task("T1", 2)
t.priority = 5               # FrozenInstanceError!

from dataclasses import replace
t2 = replace(t, priority=5)  # make a modified COPY instead
```

Frozen dataclasses can be put in sets and used as dict keys (they're hashable).
If code "updates" a frozen object, check that it uses the returned copy:

```python
replace(task, status="done")            # BUG: result thrown away
task = replace(task, status="done")     # correct
```

### Other dataclass helpers

```python
from dataclasses import asdict
asdict(c)     # {"id": "C01", "name": "Ana", ...}  handy for JSON output
```

---

## 1.10 Enum: a fixed set of named values

```python
from enum import Enum

class State(Enum):
    ACTIVE = "active"
    OVERLOADED = "overloaded"
    UNREACHABLE = "unreachable"

s = State.ACTIVE
s.value                 # "active"
s.name                  # "ACTIVE"
State("active")         # State.ACTIVE (look up by value)
s == State.ACTIVE       # True
s == "active"           # False!  an Enum member is not equal to its plain value
```

A common bug: comparing an Enum to a string, or the other way round.

---

## 1.11 The `collections` module

### defaultdict: a dict with an automatic default for missing keys

```python
from collections import defaultdict

groups = defaultdict(list)
groups["A"].append(1)        # no KeyError: groups["A"] starts as []

totals = defaultdict(int)    # missing keys start at 0
totals["x"] += 5

voters = defaultdict(set)    # missing keys start as set()
```

**Trap:** even *reading* a missing key adds it:

```python
d = defaultdict(list)
d["ghost"]           # now d has a "ghost" key with []
len(d)               # 1  <- this can break counts and reports
"ghost" in d         # True
# Use d.get("ghost") to read without adding.
```

### Counter: count things

```python
from collections import Counter

counts = Counter(["bug", "billing", "bug"])   # Counter({'bug': 2, 'billing': 1})
counts["bug"]               # 2
counts["missing"]           # 0 (no KeyError, and NOT inserted)
counts.most_common(1)       # [('bug', 2)]
counts.update(["bug"])      # add more
counts["x"] += 1
```

`most_common` breaks ties by **insertion order**. If the spec says "ties broken
alphabetically", `most_common` alone is wrong:

```python
top = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[0]
```

### deque: a fast queue

```python
from collections import deque
q = deque([1, 2])
q.append(3)        # add right
q.popleft()        # remove left, fast (list.pop(0) is slow)
```

---

## 1.12 Sorting (the #1 bug location in the debug sets)

```python
sorted(xs)                          # ascending
sorted(xs, reverse=True)            # descending
sorted(items, key=lambda p: p.priority)          # by one field
sorted(items, key=lambda p: (p.priority, p.id))  # by priority, ties broken by id
```

### How tuple keys work

Python compares tuples position by position: first elements, and only if those
are equal, the second elements, and so on.

```python
(1, "B") < (1, "C") < (2, "A")      # True
```

### Mixing directions: negate the numeric part

"Highest rating first, then oldest join date, then id A to Z":

```python
sorted(cands, key=lambda c: (-c.rating, c.joined, c.id))
#                             ^ minus = descending for numbers
```

`reverse=True` reverses **every** level, including the tie-breaks. So
`sorted(x, key=lambda c: (c.rating, c.id), reverse=True)` puts the ids Z to A,
which is usually not what the spec wants.

You can't negate strings or dates. Either sort twice (Python's sort is
**stable**: equal items keep their previous order), or convert dates to a number:

```python
xs.sort(key=lambda c: c.id)                     # secondary key first
xs.sort(key=lambda c: c.score, reverse=True)    # primary key last
```

### Handling None in sort keys

```python
sorted(cands, key=lambda c: c.joined)   # TypeError if any joined is None
sorted(cands, key=lambda c: (c.joined or date.max))   # None sorts last
sorted(cands, key=lambda c: (c.joined is None, c.joined or date.min))  # also works
```

### Priority-meaning check

Every set defines priority differently. Always ask:

1. In the **spec**, is `1` the most important, or is a **bigger** number more important?
2. Does the sort put the most important item **first**?
3. What are the tie-break rules, in order?

### Sorting strings: numbers as text

```python
sorted(["10", "9", "2"])        # ['10', '2', '9']  (text order!)
sorted(["10", "9", "2"], key=int)   # ['2', '9', '10']
sorted(["b", "A", "a"])         # ['A', 'a', 'b']   (uppercase before lowercase)
```

---

## 1.13 Exceptions (errors)

```python
try:
    value = int(text)
except ValueError:
    value = None                 # handle a specific error
except (TypeError, KeyError) as exc:
    print(exc)                   # catch several types; `exc` is the error object
else:
    print("runs only if NO exception")
finally:
    print("ALWAYS runs (cleanup)")
```

### Raising

```python
raise ValueError(f"unrecognised date: {value!r}")

class IngestError(Exception):    # your own error type
    pass

try:
    data = json.loads(text)
except json.JSONDecodeError as exc:
    raise InvalidOutput("not JSON") from exc   # "from exc" keeps the original cause
```

### The try-each-format loop (from a loader)

```python
for fmt in DATE_FORMATS:
    try:
        return datetime.strptime(text, fmt).date()   # success: return immediately
    except ValueError:
        continue                                      # failed: try the next format
raise ValueError(...)                                 # none worked
```

### Dangerous patterns to look for

```python
except Exception:   # catches EVERYTHING, which can hide real bugs
    pass
except:             # even worse: also catches Ctrl+C
```

Common error types: `ValueError` (bad value), `KeyError` (missing dict key),
`IndexError` (list index out of range), `TypeError` (wrong type, e.g. `None + 1`),
`AttributeError` (`None.strip()`), `FileNotFoundError`, `ZeroDivisionError`.

---

## 1.14 Files, CSV, JSON, paths, dates

### pathlib.Path

```python
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
#          ^ this file   ^ absolute  ^ its folder ^ up one   ^ "/" joins paths

p = DATA_DIR / "contributors.csv"
p.exists()      p.name  # "contributors.csv"
p.suffix        # ".csv"     p.stem  # "contributors"
p.read_text(encoding="utf-8")
p.write_text("hi", encoding="utf-8")
p.parent.mkdir(parents=True, exist_ok=True)   # create folders, no error if they exist
```

### `with open(...)`: files that close themselves

```python
with open(path, newline="", encoding="utf-8") as fh:
    ...     # file is open here
# file is closed automatically here, even if an error happened
```

`with` is a **context manager**. Locks (`with lock:`) and thread pools
(`with ThreadPoolExecutor() as pool:`) use the same syntax.

### CSV

```python
import csv

with open(path, newline="", encoding="utf-8") as fh:
    for row in csv.DictReader(fh):           # each row is a dict keyed by the header
        cid = row["contributor_id"]          # values are ALWAYS strings ("" if blank)
```

- Every value is a **string**: `"4.5"`, `"0"`, `""`. Convert with `int()`/`float()`.
- A blank cell is `""`, so `int("")` raises ValueError. Hence `int(x or 0)`.
- If a row has **fewer** columns than the header, the missing ones are `None`.
  If it has **more**, the extras go under the key `None`.
- Header names can have stray spaces too (`" priority"`).
- `newline=""` lets the csv module handle quoted fields containing newlines.
- `encoding="utf-8-sig"` strips a BOM (an invisible character some programs put
  at the start of a file).
- Reading from bytes (e.g. an upload): `text = data.decode("utf-8")`, then
  `csv.reader(io.StringIO(text))`. `decode` raises `UnicodeDecodeError` on bad bytes.

```python
csv.reader(fh)                 # rows as lists instead of dicts
writer = csv.DictWriter(fh, fieldnames=["a", "b"]); writer.writeheader(); writer.writerow({...})
```

### JSON

```python
import json

data = json.load(fh)                  # file -> Python
data = json.loads('{"a": 1}')         # string -> Python  (s = string)
json.dump(obj, fh, indent=2)          # Python -> file
text = json.dumps(obj, indent=2)      # Python -> string
```

| JSON | Python |
|---|---|
| object `{}` | dict |
| array `[]` | list |
| string | str |
| number | int / float |
| `true` / `false` | `True` / `False` |
| `null` | `None` |

- JSON object keys are always strings. `{1: "a"}` saves as `{"1": "a"}` and
  loads back with the key `"1"`.
- Sets and dataclasses can't be dumped directly: use `sorted(the_set)` and `asdict(obj)`.
- `isinstance(True, int)` is `True` in Python, so "confidence must be a number,
  not a boolean" needs an explicit `bool` check first.

**JSONL** (JSON Lines) = one JSON object per line:

```python
for line in fh:
    if line.strip():
        rec = json.loads(line)
```

### datetime

```python
from datetime import date, datetime, timedelta, timezone

datetime.strptime("03/15/2022", "%m/%d/%Y")     # parse with an explicit format
datetime.strptime("5 Jan 2023", "%d %b %Y")
d.strftime("%Y-%m-%d")                          # format to a string
datetime.fromisoformat("2024-01-05T10:00:00+00:00")
datetime.fromisoformat(s.replace("Z", "+00:00")) # older Pythons don't accept "Z"
dt.date()                                       # datetime -> date
date.max / date.min                             # biggest / smallest possible date
d2 - d1                                         # a timedelta
(d2 - d1).days
dt + timedelta(seconds=30)
```

Format codes: `%Y` 4-digit year, `%m` month number, `%d` day, `%b` short month
name (Jan), `%H:%M:%S` time.

Traps:
- `03/04/2024` is March 4 under `%m/%d/%Y` but 3 April under `%d/%m/%Y`. Check the spec.
- Comparing a `date` with a `datetime`, or a timezone-aware datetime with a naive
  one, raises TypeError.
- Comparing dates **as strings** only works for `YYYY-MM-DD`.

### Decimal: exact money maths

```python
from decimal import Decimal, ROUND_HALF_UP
Decimal("0.1") + Decimal("0.2") == Decimal("0.3")     # True
Decimal("2.675").quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)  # Decimal('2.68')
Decimal(0.1)     # BUG-prone: builds from the inexact float. Pass a string instead.
```

### Regular expressions (`re`)

```python
import re
EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
EMAIL.match("a@b.co")        # a Match object (truthy) or None
re.fullmatch(r"\d+", "123")  # whole string must match
re.findall(r"\d+", "a1b22")  # ['1', '22']
re.search(r"<item>(.*?)</item>", text, re.S).group(1)   # first match's captured group
```

`r"..."` is a raw string, so backslashes stay as typed. `^` = start, `$` = end,
`\d` digit, `\s` whitespace, `[^@]` any char except @, `+` one or more,
`*` zero or more, `?` optional, `(...)` capture group.

---

## 1.15 Testing: unittest and pytest

### unittest (the debug sets)

```python
import unittest
from staffing.reports import build_report

class TestAssignment(unittest.TestCase):
    @classmethod
    def setUpClass(cls):              # runs ONCE before all tests in this class
        cls.report = build_report()

    def setUp(self):                  # runs before EACH test (if defined)
        ...

    def test_paused_project_gets_nobody(self):     # must start with test_
        self.assertEqual(self.report["assignments"]["P05"], [])

    def test_full_table(self):
        self.maxDiff = None           # show the FULL diff on failure, not a cut-off one
        self.assertEqual(self.report["assignments"], EXPECTED)
```

Assertions: `assertEqual(a, b)`, `assertTrue(x)`, `assertIn(x, coll)`,
`assertAlmostEqual(a, b, places=2)`, `assertRaises(ValueError)`,
`assertDictEqual`, `assertListEqual`.

### pytest (the backend sets; also runs unittest files)

```python
def test_health(tmp_path):             # a plain function; tmp_path = a fresh temp folder
    client = TestClient(create_app(storage_dir=tmp_path))
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}

import pytest
def test_bad_value():
    with pytest.raises(ValueError):
        parse("garbage")

@pytest.mark.parametrize("text,expected", [("yes", True), ("no", False), ("", False)])
def test_flag(text, expected):
    assert parse_flag(text) is expected
```

**Fixtures** are arguments pytest fills in for you: `tmp_path` (temp folder),
`monkeypatch` (temporarily replace things), or your own:

```python
@pytest.fixture
def client(tmp_path):
    return TestClient(create_app(storage_dir=tmp_path))

def test_get_missing(client):          # pytest passes the fixture's return value
    assert client.get("/uploads/nope").status_code == 404
```

`conftest.py` is a file pytest loads automatically. Shared fixtures and import
path setup go there.

### Running tests

```bash
python -m pytest                       # all tests
python -m pytest -q                    # quieter output
python -m pytest -x                    # stop at the first failure
python -m pytest tests/test_1_assignment.py              # one file
python -m pytest tests/test_1_assignment.py::TestAssignment::test_full_table   # one test
python -m pytest -k "paused"           # tests whose name contains "paused"
python -m pytest -s                    # show print() output
python -m unittest discover -s tests -v   # the unittest way
```

### Reading a failure

```
AssertionError: Lists differ: ['C07', 'C06'] != ['C06', 'C07']
First differing element 0:
'C07'
'C06'
```

The **left** value is what your code produced, the **right** value is what the
test expected (for `assertEqual(actual, expected)`). Here the items are right but
the order is wrong, which points at a sort or tie-break.

---

## 1.16 Concurrency: threads and asyncio (backend sets, a few debug sets)

### Threads and Locks

Threads run code "at the same time". If two threads read-modify-write the same
data, updates can get lost (a **race condition**). A `Lock` lets only one thread
into a block at a time.

```python
import threading

class Counter:
    def __init__(self):
        self._lock = threading.Lock()
        self.n = 0

    def incr(self):
        with self._lock:          # acquire; released automatically at the end of the block
            self.n += 1
```

### ThreadPoolExecutor: run a function over many items in parallel

```python
from concurrent.futures import ThreadPoolExecutor

with ThreadPoolExecutor(max_workers=4) as pool:
    results = list(pool.map(classify, tickets))   # results come back in INPUT order
```

Useful for slow, I/O-bound calls (HTTP, LLM). `max_workers` caps concurrency.

### asyncio: `async` / `await`

```python
import asyncio

async def fetch(x):            # "coroutine function": calling it does NOT run it yet
    await asyncio.sleep(1)     # pause here and let other tasks run
    return x * 2

async def main():
    one = await fetch(1)                                  # run one, wait for it
    many = await asyncio.gather(*(fetch(i) for i in range(5)))   # run 5 concurrently
    return many                                           # results in input order

asyncio.run(main())            # start the event loop from normal code
```

- `await` only works inside `async def`.
- Forgetting `await` is a classic bug: `result = fetch(1)` gives you a
  coroutine object, not the value, and Python warns "coroutine was never awaited".
- `time.sleep()` inside async code **blocks everything**. Use `await asyncio.sleep()`.
- Limiting concurrency:

```python
sem = asyncio.Semaphore(4)
async def limited(x):
    async with sem:            # at most 4 tasks inside this block at once
        return await fetch(x)
```

- Running blocking code from async code: `await asyncio.to_thread(blocking_fn, arg)`.

---

# PART 2: THE DEBUGGING ROUND

## 2.1 What the round is

You get an unfamiliar multi-file repo, data files, a README with the spec, and
numbered failing tests. You must fix **every** bug and explain where and why it
fails. Rules: don't edit tests, data, or `# VERIFIED` code.

## 2.2 Method (do it in this order)

1. **Read the README spec first.** Write down every rule: priority direction,
   tie-breaks, inclusive/exclusive limits, how blanks are treated, ID
   normalisation. The spec is the source of truth, not the comments.
2. **Look at the data files.** Spot the messiness: `"c02 "`, `" C06"`, mixed date
   formats, blank cells, `Yes`/`TRUE`/`y`, a headcount of `0`, a priority of `" 8"`.
3. **Run the tests** and read the first failure carefully.
4. **Trace the data flow** from `main.py`: loader -> models -> core logic -> report.
   For each step ask "what goes in, what comes out?"
5. **Print intermediate values** to find the first step where reality differs
   from the spec:
   ```python
   print(f"{project.id!r} {project.priority!r} {pool=}")   # {x=} prints "x=<value>"
   breakpoint()   # opens the debugger: n=next line, s=step in, p expr=print, c=continue, q=quit
   ```
6. **Fix one bug at a time and re-run.** Some bugs are **masked**: they only
   show up after an earlier bug is fixed, or only in the Test 3 report.
7. **Explain each fix** in one sentence: *file, line, what it did, what the spec
   says, the effect on output.*

You can also poke at the code interactively:

```bash
python -c "from staffing.loader import load_projects; print(load_projects())"
python -i main.py      # runs the script, then leaves you in a Python prompt
```

## 2.3 Bug patterns (what to look for)

Every example below is generic. Learn the **shape** of each bug.

| # | Pattern | Buggy shape | What to check |
|---|---|---|---|
| 1 | Sort direction / priority meaning flipped | `sorted(p, key=lambda p: p.priority)` when a higher number = more important | Spec's priority definition |
| 2 | Wrong tie-break | `key=lambda x: (-x.score,)` with no id, or `reverse=True` reversing the id too | Every tie-break in the spec, in order |
| 3 | Falsy zero | `x or default`, `if not count:` when 0 is valid | Is 0 / "" a legitimate value? |
| 4 | `"".split()` gives `[""]` | `text.split(";")` on a blank cell -> `[""]`, so `len` = 1 | Filter empties: `if p.strip()` |
| 5 | `bool("false")` | `bool(row["active"])` | Compare to a set of truthy strings |
| 6 | Off-by-one | `<` vs `<=`, `range(n)` vs `range(1, n+1)`, `[:n-1]` | "at most", "after", "expires at" |
| 7 | Wrong field / key | `row["course"]` instead of `row["required_course"]`; `task.created` vs `task.updated` | Compare names against the spec/header |
| 8 | ID normalisation mismatch | loader does `.upper()`, lookup doesn't; one side `.strip()`s | Every create/compare site |
| 9 | Check missing | eligibility ignores a required condition | Each rule in the spec has code |
| 10 | State never updated | `taken` set never `.add()`ed; counter never incremented; `replace(...)` result discarded | Mutations actually happen |
| 11 | Wrong aggregation | `max` vs `sum`, average over the wrong count, counting duplicates | Count by hand on 2-3 rows |
| 12 | Mutable shared default | `def f(x, acc=[])`, a class-level list | Shared state across calls |
| 13 | Integer division / rounding | `//` vs `/`, `int()` truncating, rounding too early | Round only at the end, as the spec says |
| 14 | Wrong variable in a loop | using `items` instead of `item`, or the last loop value after the loop | Names inside loops |
| 15 | Date parsing | `%m/%d` vs `%d/%m`, comparing as strings, timezones | Formats in the data |
| 16 | defaultdict read inserts keys | `if totals[k]:` adds `k` | Report counts/keys |
| 17 | `return` inside the loop | `for x in xs: ... return result` (returns after the first item) | Indentation! |
| 18 | Early `break`/`continue` | skips work that should still happen | Loop control |

### Indentation is part of the logic

```python
for p in projects:
    total += p.cost
    return total        # BUG: returns after the FIRST project

for p in projects:
    total += p.cost
return total            # correct: after the loop
```

## 2.4 How to explain a bug (what interviewers want)

> "In `rules.py` line 12, eligibility never checks the required course. The spec
> says a contributor needs the course to join project X. Because of that, C08 was
> assigned to P01 without ML-101. I added the course check, and now Test 1 passes
> and P01 gets C01 and C15."

That covers location, cause, spec reference, observable symptom, and the fix.

---

# PART 3: THE BACKEND ROUND

## 3.1 What the round is

60 minutes, in parts (Part 1 -> 2 -> 3), each building on the last. Typically:
build an HTTP API (upload a file, validate, save), then call an LLM with retries
and persist results, then add something like async jobs, rate limiting, or
caching. You're graded on working code, debugging yourself, production quality
(error handling, validation), **tests**, and how you explain your choices.

## 3.2 HTTP basics

A client sends a **request**: method + path (+ query string, headers, body). The
server replies with a **response**: status code + headers + body (usually JSON).

```
POST /uploads HTTP/1.1          <- method and path
Content-Type: multipart/form-data
<file bytes>

HTTP/1.1 201 Created            <- status code
Content-Type: application/json
{"upload_id": "ab12", "valid_rows": 9}
```

| Method | Meaning |
|---|---|
| GET | read something (no body; must not change data) |
| POST | create something / trigger an action |
| PUT | replace something |
| PATCH | partially update |
| DELETE | delete |

Parts of a URL: `/uploads/{upload_id}/classify?limit=10`
- **path parameter**: `upload_id` (identifies a resource)
- **query parameter**: `limit=10` (options/filters)

### Status codes you will use

| Code | Name | Use when |
|---|---|---|
| 200 | OK | successful GET / action |
| 201 | Created | POST created a new resource |
| 202 | Accepted | job queued, will finish later (async jobs) |
| 204 | No Content | success, empty body |
| 400 | Bad Request | input is malformed (empty file, bad header, invalid UTF-8) |
| 404 | Not Found | the id doesn't exist |
| 409 | Conflict | duplicate / already exists / state doesn't allow this (e.g. double booking) |
| 413 | Payload Too Large | file too big |
| 415 | Unsupported Media Type | wrong file type (`.txt` when `.csv` is required) |
| 422 | Unprocessable Entity | FastAPI's automatic "request didn't match the declared shape" (e.g. missing field) |
| 429 | Too Many Requests | rate limited; send a `Retry-After` header |
| 500 | Internal Server Error | unexpected crash (a bug) |
| 502/503/504 | Bad Gateway / Unavailable / Timeout | an upstream dependency failed |

Rule of thumb: **4xx = the client's fault, 5xx = the server's fault.** Only 429
and 5xx are usually worth retrying.

## 3.3 FastAPI

FastAPI is a web framework. You declare functions, and it turns them into HTTP
endpoints, reading the type hints to parse and validate input.

### Minimal app

```python
from fastapi import FastAPI, HTTPException

app = FastAPI(title="Demo")

@app.get("/health")
def health() -> dict:
    return {"status": "ok"}           # dicts/lists are converted to JSON automatically

@app.get("/items/{item_id}")          # path parameter
def get_item(item_id: str, verbose: bool = False):   # verbose comes from ?verbose=true
    item = DB.get(item_id)
    if item is None:
        raise HTTPException(status_code=404, detail=f"item {item_id} not found")
    return item                       # error body: {"detail": "item x not found"}

@app.post("/items", status_code=201)  # change the success status code
def create_item(...):
    ...
```

Run it: `uvicorn app.main:app --reload`, then open `http://127.0.0.1:8000/docs`
for an auto-generated page where you can try each endpoint.
(`app.main:app` means "module `app/main.py`, variable `app`".)

### JSON request bodies: Pydantic models

```python
from pydantic import BaseModel, Field

class ReserveRequest(BaseModel):
    user_id: str
    seats: int = Field(gt=0)          # must be > 0, otherwise FastAPI returns 422
    note: str | None = None

@app.post("/reservations", status_code=201)
def reserve(req: ReserveRequest):     # FastAPI parses and validates the JSON body
    return {"user": req.user_id, "seats": req.seats}
```

### File uploads

```python
from fastapi import File, UploadFile

@app.post("/uploads", status_code=201)
async def upload(file: UploadFile = File(...)):   # File(...) = required form field named "file"
    name = file.filename or ""
    if not name.lower().endswith(".csv"):
        raise HTTPException(415, "only .csv files are accepted")
    raw: bytes = await file.read()                # read() is async, so the function is async
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise HTTPException(400, "file is not valid UTF-8")
    ...
```

- Needs the `python-multipart` package (it's in `requirements.txt`).
- A missing `file` field gets **422 automatically**; you don't write that.

### Headers

```python
from fastapi import Header

@app.post("/jobs")
def create_job(idempotency_key: str | None = Header(default=None)):  # reads "Idempotency-Key"
    ...
```

To *send* a custom header or status, return a `JSONResponse`:

```python
from fastapi.responses import JSONResponse
return JSONResponse(status_code=429, content={"detail": "slow down"}, headers={"Retry-After": "2"})
```

### The app factory pattern (`create_app`)

```python
def create_app(storage_dir="storage", llm=None, clock=None, max_concurrency=4) -> FastAPI:
    storage_dir = Path(storage_dir)
    llm = llm or make_llm()
    clock = clock or RealClock()
    app = FastAPI()

    @app.get("/uploads/{upload_id}")
    def get_upload(upload_id: str):
        ...   # can use storage_dir, llm, clock (closure)

    return app

app = create_app()     # the default app uvicorn runs
```

**Why:** tests build their own app with a temp folder, a fake LLM, and a fake
clock, so tests are fast, isolated, and repeatable. Keep the signature exactly
as given. The interviewer's hidden tests call it.

Endpoints are defined **inside** `create_app`, and that's normal.

### Testing endpoints

```python
from fastapi.testclient import TestClient

def test_upload(tmp_path):
    client = TestClient(create_app(storage_dir=tmp_path))
    with open("data/tickets.csv", "rb") as fh:
        resp = client.post("/uploads", files={"file": ("tickets.csv", fh, "text/csv")})
    assert resp.status_code == 201
    body = resp.json()
    assert body["valid_rows"] == 9

    # build a file in memory instead of reading from disk:
    resp = client.post("/uploads", files={"file": ("x.csv", b"ticket_id\n", "text/csv")})

    resp = client.post("/reservations", json={"user_id": "u1", "seats": 2})   # JSON body
    resp = client.get("/items/1", params={"verbose": "true"}, headers={"Idempotency-Key": "k1"})
```

`TestClient` calls the app directly, with no real server or network.

### `httpx`: calling other HTTP services

```python
import httpx
resp = httpx.get("http://localhost:8001/x", timeout=5.0)
resp.status_code;  resp.json();  resp.headers.get("Retry-After")
resp.raise_for_status()          # raises for 4xx/5xx
```

## 3.4 Ingestion: validate rows and report bad ones

The usual shape of an upload endpoint:

```python
def ingest(text):
    reader = csv.reader(io.StringIO(text))
    header = next(reader, None)                      # None if the file is empty
    if header is None:
        raise IngestError("empty file")
    header = [h.strip() for h in header]
    missing = REQUIRED - set(header)
    if missing:
        raise IngestError(f"missing columns: {sorted(missing)}")
    idx = {name: i for i, name in enumerate(header)}   # column name -> position

    good, errors, seen, row_no = [], [], set(), 0
    for values in reader:
        if not any(v.strip() for v in values):       # skip completely blank lines
            continue
        row_no += 1
        if len(values) != len(header):
            errors.append({"row": row_no, "field": None, "message": "wrong number of columns"})
            continue
        rec = {k: values[idx[k]].strip() for k in REQUIRED_ORDER}
        err = first_error(rec, seen)                 # check rules IN SPEC ORDER
        if err:
            errors.append({"row": row_no, **err})
            continue
        seen.add(rec["ticket_id"])                   # only VALID rows reserve the id
        good.append(rec)
    return good, errors
```

Key ideas: separate "whole file is bad" (400) from "this row is bad" (report it
and keep going); number rows exactly as the spec says; apply rules in the
specified order; return a summary.

### Saving locally

```python
import json, uuid

upload_id = uuid.uuid4().hex                          # random unique id
path = storage_dir / "uploads" / f"{upload_id}.json"
path.parent.mkdir(parents=True, exist_ok=True)

# Atomic write: write a temp file, then rename. Readers never see a half-written file.
tmp = path.with_suffix(".tmp")
tmp.write_text(json.dumps(doc), encoding="utf-8")
tmp.replace(path)

# Loading:
if not path.exists():
    return None        # the endpoint turns None into a 404
doc = json.loads(path.read_text(encoding="utf-8"))
```

Never build a path straight from user input without checking it
(`"../../etc/passwd"`). Validate that ids look like what you generate.

## 3.5 Calling an LLM reliably

The mock LLM behaves like a real one: sometimes slow, rate-limited (429),
broken (5xx), timing out, wrapping JSON in ```` ```json ```` fences, returning
broken JSON, or inventing labels.

### 1. Build the prompt

Put the user's content inside the delimiter the spec requires (e.g.
`<item>...</item>`), state the allowed labels, and ask for JSON only.

### 2. Parse defensively

```python
def parse_output(text):
    text = text.strip()
    if text.startswith("```"):                      # strip a markdown fence
        text = text.split("\n", 1)[1] if "\n" in text else ""
        text = text.rstrip().removesuffix("```")
    data = json.loads(text)                         # may raise json.JSONDecodeError
    if not isinstance(data, dict):
        raise InvalidOutput("not an object")
    label = data.get("label")
    if not isinstance(label, str) or label.strip().lower() not in LABELS:
        raise InvalidOutput(f"bad label {label!r}")
    conf = data.get("confidence")
    if isinstance(conf, bool) or not isinstance(conf, (int, float)) or not 0 <= conf <= 1:
        raise InvalidOutput(f"bad confidence {conf!r}")
    return label.strip().lower(), float(conf)
```

`isinstance(x, (int, float))` checks "is x an int OR a float". The separate
`bool` check is needed because `True` counts as an int.

### 3. Retry with a limit, exponential backoff, and jitter

```python
import random, time

def call_with_retries(llm, prompt, max_attempts=3, base=0.5, cap=8.0, sleep=time.sleep):
    last_error = None
    for attempt in range(1, max_attempts + 1):           # 1, 2, 3
        try:
            resp = llm.complete(prompt, timeout=10)
            return parse_output(resp.text), attempt      # success
        except LLMError as exc:
            if not exc.retryable:                        # e.g. 400 / auth error: give up now
                return None, attempt, str(exc)
            last_error = str(exc)
            delay = getattr(exc, "retry_after", None)    # server told us how long to wait
        except (json.JSONDecodeError, InvalidOutput) as exc:
            last_error = str(exc)
            delay = None
        if attempt < max_attempts:                       # don't sleep after the last try
            backoff = min(cap, base * 2 ** (attempt - 1))    # 0.5, 1, 2, 4 ... capped
            sleep(delay if delay is not None else random.uniform(0, backoff))  # jitter
    return None, max_attempts, last_error
```

- **Retry only retryable failures**: timeouts, 429, 5xx, invalid output.
  Don't retry a 400 or a non-retryable error.
- **Exponential backoff**: wait longer after each failure so you don't pile onto
  a struggling service.
- **Jitter** (randomness): stops many clients from retrying at the same instant
  (the "thundering herd").
- **Respect `Retry-After`** on 429.
- **Cap** the attempts and the delay.
- **Count attempts precisely.** Off-by-one here is common.
- One failed item shouldn't fail the whole request. Record it as `failed` with
  the error and continue.
- Use the **injected clock/sleep** in code you test, so tests don't actually wait.

### 4. Other LLM concerns (follow-up questions)

- **Inconsistent answers** to the same input: cache by input hash, majority-vote
  over several calls, set temperature 0, validate with a schema.
- **Cost**: count tokens per call, cache repeated inputs, batch several items per call.
- **Caching**: key = `hashlib.sha256(prompt.encode()).hexdigest()`, ideally with an expiry (TTL).

## 3.6 Fake clocks and determinism

```python
class FakeClock:
    def __init__(self, t=0.0): self.t = t
    def now(self): return self.t
    def sleep(self, s): self.t += s      # "sleeping" just moves time forward instantly
    def advance(self, s): self.t += s
```

Anything time-based (leases, TTL caches, rate limits, heartbeats, backoff) should
read time from the injected clock (`clock.now()`), never call `time.time()`
directly. Then tests can say "advance 31 seconds" and check that the lease
expired, with no real waiting. Seeded randomness (`random.Random(seed)`) makes
failures reproducible in the same way.

## 3.7 Common backend topics (Part 2 / Part 3 material)

### Idempotency keys

A client retries a POST after a timeout. Did the first one go through? Send an
`Idempotency-Key` header. The server stores `key -> response`, and a repeat with
the same key returns the stored response instead of doing the work twice. Same
key with a **different** body should return 409/422.

### Rate limiting: token bucket

```python
class TokenBucket:
    def __init__(self, capacity, refill_per_sec, clock):
        self.capacity, self.rate, self.clock = capacity, refill_per_sec, clock
        self.tokens, self.last = capacity, clock.now()

    def allow(self):
        now = self.clock.now()
        self.tokens = min(self.capacity, self.tokens + (now - self.last) * self.rate)
        self.last = now
        if self.tokens >= 1:
            self.tokens -= 1
            return True
        return False           # caller responds 429 with Retry-After
```

Keep one bucket per user/tenant: `buckets = defaultdict(lambda: TokenBucket(...))`.
The alternative is a **sliding window**: keep the timestamps of recent requests,
drop those older than the window, and allow if fewer than N remain.

### Async jobs

When work is slow, return immediately with `202 {"job_id": ..., "status": "queued"}`.
Workers process jobs in the background; the client **polls**
`GET /jobs/{id}` -> `queued | running | succeeded | failed`. Jobs that fail
too many times go to a **dead-letter queue** for humans to inspect.

### Leases (claiming tasks)

A worker "claims" a task for N seconds. If it doesn't finish or renew in time,
the lease expires and another worker can claim it. Watch the boundary
(`now >= expires_at`?) and make sure only the lease holder can complete the task.

### State machines

A task moves through allowed states only, e.g.
`pending -> in_progress -> submitted -> approved | rejected`. Keep a dict of
allowed transitions and reject anything else (409):

```python
ALLOWED = {"pending": {"in_progress"}, "in_progress": {"submitted", "pending"}, ...}
if new not in ALLOWED.get(task.state, set()):
    raise HTTPException(409, f"cannot go from {task.state} to {new}")
```

### Race conditions and double-booking

Two requests check "is the seat free?" at the same moment, both see yes, and
both book it. Fix it by doing the check and the write under one lock (or, in a
real database, a transaction/unique constraint).

### Caching with TTL

Store `(value, expires_at)`. On read, if `clock.now() >= expires_at`, treat it as
missing and refetch.

### Priority queues

```python
import heapq
heap = []
heapq.heappush(heap, (priority, seq, task))   # smallest first; seq breaks ties FIFO
priority, _, task = heapq.heappop(heap)
```

For "highest first", push `-priority`.

### Load balancer with heartbeats

Workers send heartbeats. If one is silent past a timeout, mark it `unreachable`
and stop routing to it; if it's over capacity, mark it `overloaded`. Route new
tasks to the least-loaded `active` worker, and reassign in-flight tasks from a
dead worker (failover).

## 3.8 "How would you scale this 100x?" talking points

- **Storage:** local JSON files -> a database (Postgres) and object storage (S3) for raw files.
- **Slow work:** move it off the request path into a queue (SQS/Redis/Kafka) plus a worker pool; return 202 + job id.
- **LLM limits:** client-side rate limiting, bounded concurrency, batching, caching, backoff; a circuit breaker to stop calling a failing service.
- **Large files:** stream row by row instead of reading the whole file into memory.
- **Many servers:** shared state (locks, rate limits, idempotency keys) must move to a shared store like Redis or the database.
- **Observability:** structured logs, metrics (latency, error rate, retries, cost), alerts.
- **Correctness under retries:** idempotency keys, at-least-once delivery + dedupe.

## 3.9 What "production quality" means in the rubric

- Validate input and return the **specified** status codes and error shape.
- No crash on a bad row: report it and continue.
- Small functions with clear names (`parse_row`, `save_upload`, `classify_ticket`).
- No hard-coded paths; use the injected `storage_dir`, `llm`, `clock`.
- **Tests for the unhappy paths:** empty file, bad header, duplicate ids, LLM
  failures, retries exhausted, 404s.
- Talk while you work: say what you're checking and why.

---

# PART 4: CHEAT SHEETS

## 4.1 Read-this-line quick reference

| You see | It means |
|---|---|
| `x = y or z` | y if y is truthy, else z (watch out for 0 / "") |
| `a if cond else b` | one-line if/else |
| `[f(x) for x in xs if c]` | build a list |
| `{k: v for ...}` / `{x for ...}` | build a dict / a set |
| `sum(1 for r in rows if r.ok)` | count matching items |
| `lambda p: (p.a, -p.b)` | small function; sort by a ascending, then b descending |
| `xs[:n]` / `xs[-1]` | first n / last item |
| `d.get(k, 0)` | value or 0 if the key is missing |
| `d.setdefault(k, []).append(v)` | group v under k |
| `defaultdict(list)` | dict whose missing keys start as [] |
| `Counter(xs)` | count occurrences |
| `@dataclass(frozen=True)` | immutable data object |
| `field(default_factory=set)` | a fresh empty set per object |
| `str \| None` | "a string or None" (type hint only) |
| `-> dict` | the function returns a dict (hint only) |
| `*args, **kwargs` | any extra positional / keyword arguments |
| `def f(a, *, b)` | b must be passed by name |
| `{**a, "k": 1}` | copy dict a and set k |
| `f"{x!r}"` | repr of x, with quotes, good for debugging |
| `with open(...) as fh:` | open file, auto-close |
| `with self._lock:` | only one thread at a time in this block |
| `async def` / `await` | coroutine / wait for one |
| `@app.post("/x", status_code=201)` | register a POST endpoint |
| `raise HTTPException(404, "...")` | return an error response |
| `Path(__file__).resolve().parent` | this file's folder |
| `raise X from exc` | raise a new error, keeping the cause |
| `if __name__ == "__main__":` | run only when executed directly |

## 4.2 Debugging-round checklist

- [ ] Read the spec; list priority direction, tie-breaks, boundaries, blank handling
- [ ] Skim the data for messy values
- [ ] Run the tests; read the diff (actual vs expected)
- [ ] Trace main -> loader -> logic -> report; print intermediate values with `!r`
- [ ] Check every sort: direction, tie-break, `reverse=True` side effects
- [ ] Check every `or`, `if not x`, and `bool(...)` for the falsy-zero / string-bool trap
- [ ] Check every `.split()` on possibly empty text
- [ ] Check ID normalisation at every create/compare site
- [ ] Check `<` vs `<=`, ranges, slices
- [ ] Check that every rule in the spec has code
- [ ] Check that state actually updates (sets, counters, returned copies)
- [ ] After each fix, re-run; look for masked bugs
- [ ] Don't touch tests, data, or `# VERIFIED`

## 4.3 Backend-round checklist

- [ ] Read the PART file twice; list endpoints, status codes, the response shape
- [ ] Keep `create_app(...)` and its signature; use the injected deps
- [ ] Happy path working end to end first, then the error cases
- [ ] Write tests as you go (TestClient + `tmp_path` + a configured fake LLM)
- [ ] LLM: parse defensively, validate, retry only retryable errors, cap attempts, backoff + jitter
- [ ] Persist results; GET endpoints return 404 when missing
- [ ] Be ready to discuss rate limits, async jobs, idempotency, and scaling 100x

## 4.4 Glossary

- **API / endpoint:** a URL + method the server responds to.
- **Backoff:** waiting longer between retries.
- **Coroutine:** what an `async def` function returns; run it with `await`.
- **Dead-letter queue:** where permanently failed jobs go.
- **Dependency injection:** passing collaborators (LLM, clock, storage) in, instead of creating them inside.
- **Fixture:** a pytest-provided test argument (`tmp_path`, `monkeypatch`).
- **Idempotent:** doing it twice has the same effect as once.
- **Jitter:** random variation added to backoff delays.
- **Lease:** a time-limited claim on a task.
- **Masked bug:** a bug hidden behind another one.
- **Race condition:** a bug that depends on the timing of concurrent operations.
- **Red herring:** code that looks wrong but is correct (`# VERIFIED`).
- **Stable sort:** equal items keep their original relative order.
- **TTL:** time-to-live; how long a cached value is valid.
- **Truthy / falsy:** how a value behaves in `if`.
