"""Tests for task scheduler."""

from scheduler import TaskScheduler, connect_pipeline, get_default_scheduler


def test_scheduler_register_run():
    s = TaskScheduler()
    ran = []
    s.register("data_update", lambda: ran.append("data_update"))
    s.run("data_update")
    assert "data_update" in ran


def test_connect_pipeline():
    s = connect_pipeline()
    assert s is not None
    ran = s.run_pipeline()
    assert isinstance(ran, list)
