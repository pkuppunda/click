
import click
import pytest
from click.testing import CliRunner

import log_watch as logwatcher


@pytest.fixture(autouse=True)
def reset_state():
    """Keep global state isolated between tests."""
    logwatcher.counts.clear()
    logwatcher.history.clear()
    yield
    logwatcher.counts.clear()
    logwatcher.history.clear()


def test_parse_valid_log_line():
    entry = logwatcher.parse(
        "2026-10-26 12:00:00 ERROR Database connection failed"
    )

    assert entry == {
        "ts": "2026-10-26 12:00:00",
        "level": "ERROR",
        "msg": "Database connection failed",
    }


def test_parse_invalid_log_line():
    assert logwatcher.parse("This is not a valid log line") is None


def test_process_line_updates_level_counts():
    logwatcher.process_line("2026-10-26 12:00:00 INFO Started")
    logwatcher.process_line("2026-10-26 12:00:01 ERROR Failed")
    logwatcher.process_line("2026-10-26 12:00:02 ERROR Retry failed")

    assert logwatcher.counts == {"INFO": 1, "ERROR": 2}


def test_process_line_ignores_invalid_line():
    logwatcher.process_line("Invalid log entry")

    assert logwatcher.counts == {}
    assert logwatcher.history == []


def test_report_prints_counts(capsys):
    logwatcher.process_line("2026-10-26 12:00:00 INFO Started")
    logwatcher.process_line("2026-10-26 12:00:01 ERROR Failed")

    logwatcher.report()

    output = capsys.readouterr().out
    assert "counts={'INFO': 1, 'ERROR': 1}" in output


def test_report_shows_only_three_most_recent_errors(capsys):
    for i in range(4):
        logwatcher.process_line(
            f"2026-10-26 12:00:0{i} ERROR Error number {i}"
        )

    logwatcher.report()

    output = capsys.readouterr().out
    assert "Error number 0" not in output
    assert "Error number 1" in output
    assert "Error number 2" in output
    assert "Error number 3" in output


def test_cli_rejects_missing_log_file():
    runner = CliRunner()

    result = runner.invoke(
        logwatcher.watch,
        ["missing_test_file.log"],
    )

    assert result.exit_code != 0
    assert "does not exist" in result.output.lower()
