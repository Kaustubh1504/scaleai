import pytest


def test_top_labels_counts(sol):
    """top_labels returns the n most frequent labels with their counts"""
    labels = ["cat"] * 5 + ["dog"] * 3 + ["bird"]
    assert sol.top_labels(labels, 2) == [("cat", 5), ("dog", 3)]


def test_top_labels_ties_alphabetical(sol):
    """Ties are broken by label ascending, not by first appearance"""
    labels = ["zebra", "dog", "zebra", "dog", "ant", "ant", "cat"]
    assert sol.top_labels(labels, 3) == [("ant", 2), ("dog", 2), ("zebra", 2)], \
        "Counter.most_common orders ties by insertion; the statement asks for label ascending"


def test_top_labels_n_too_big(sol):
    """n larger than the number of distinct labels returns all of them; accepts a generator"""
    assert sol.top_labels((x for x in ["b", "a", "b"]), 10) == [("b", 2), ("a", 1)]


def test_group_by_annotator(sol):
    """group_by_annotator keeps task ids in input order per annotator"""
    subs = [{"annotator_id": "a2", "task_id": "t1"}, {"annotator_id": "a1", "task_id": "t2"},
            {"annotator_id": "a2", "task_id": "t3"}]
    assert sol.group_by_annotator(subs) == {"a2": ["t1", "t3"], "a1": ["t2"]}


def test_group_returns_plain_dict(sol):
    """group_by_annotator returns a plain dict: unknown annotators raise KeyError"""
    result = sol.group_by_annotator([{"annotator_id": "a", "task_id": "t"}])
    with pytest.raises(KeyError):
        result["nobody"]
    assert "nobody" not in result, "a defaultdict would have inserted the key"


def test_sliding_window_boundary(sol):
    """SlidingWindowCounter excludes an event exactly window_s old"""
    c = sol.SlidingWindowCounter(60)
    for ts in (0, 30, 61):
        c.record(ts)
    assert c.count(61) == 2, "ts=0 is 61s old, out of a 60s window"
    assert c.count(90) == 1, "at now=90, ts=30 is exactly 60s old and must be excluded"
    assert c.count(200) == 0


def test_sliding_window_many_events(sol):
    """SlidingWindowCounter handles 200k events quickly (deque, not list.pop(0))"""
    c = sol.SlidingWindowCounter(10)
    for i in range(200_000):
        c.record(i * 0.01)
        if i % 1000 == 0:
            c.count(i * 0.01)
    assert c.count(1999.99) == 1000, "1000 events (0.01s apart) fall inside a 10s window"


def test_lru_evicts_least_recent(sol):
    """LRUCache evicts the least recently used key; get() refreshes recency"""
    cache = sol.LRUCache(2)
    cache.put("a", 1)
    cache.put("b", 2)
    assert cache.get("a") == 1
    cache.put("c", 3)
    assert cache.get("b") is None, "b was least recently used and should be evicted"
    assert cache.get("a") == 1 and cache.get("c") == 3
    assert len(cache) == 2


def test_lru_update_and_default(sol):
    """LRUCache put() on an existing key updates it and marks it recent; get() honours default"""
    cache = sol.LRUCache(2)
    cache.put("a", 1)
    cache.put("b", 2)
    cache.put("a", 10)
    cache.put("c", 3)
    assert cache.get("a") == 10, "updating 'a' made it most recent, so 'b' should go"
    assert cache.get("b", "missing") == "missing"
    assert len(cache) == 2


def test_lru_bad_capacity(sol):
    """LRUCache(0) raises ValueError"""
    with pytest.raises(ValueError):
        sol.LRUCache(0)
