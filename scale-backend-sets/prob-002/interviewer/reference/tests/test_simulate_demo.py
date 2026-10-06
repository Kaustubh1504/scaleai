from lb.simulate import DEFAULT_TASKS, main


def test_demo_runs_end_to_end(capsys):
    assert main([str(DEFAULT_TASKS)]) == 0
    out = capsys.readouterr().out
    assert "ingest-001   -> w3 (attempts=2)" in out  # failed over from the hanging w2
    assert "poison-001   !!" in out
    assert "'w2': 'active'" in out
