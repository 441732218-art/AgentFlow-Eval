# (c) 2026 AgentFlow-Eval
"""Timeseries helper unit smoke (label generation)."""

from datetime import date, timedelta

from app.core.observability.timeseries import _day_labels, _label


def test_day_labels_length_and_order():
    days = _day_labels(7, end=date(2026, 7, 18))
    assert len(days) == 7
    assert days[0] == date(2026, 7, 12)
    assert days[-1] == date(2026, 7, 18)
    assert days[1] - days[0] == timedelta(days=1)


def test_label_format():
    assert _label(date(2026, 7, 18)) == "07-18"
