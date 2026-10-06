from pool.demo import DEFAULT_JOBS, main


def test_demo_runs_end_to_end(capsys):
    assert main([str(DEFAULT_JOBS)]) == 0
    out = capsys.readouterr().out
    assert "flaky-001      -> " in out and "(attempts=3)" in out
    assert "poison-001     !! dead-lettered (poison)" in out
    assert "broken-001     !! dead-lettered (max_attempts)" in out
    assert "left unfinished: []" in out
    assert "'done': 7, 'failed': 2" in out
