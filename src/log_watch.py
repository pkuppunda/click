import re
import time
from collections import Counter
from pathlib import Path

import click

LINE_RE = re.compile(r"^(?P<ts>\S+ \S+) (?P<level>[A-Z]+) (?P<msg>.*)$")

counts: Counter = Counter()
history: list[dict] = []


def parse(line: str):
    m = LINE_RE.match(line)
    return m.groupdict() if m else None
    
#def process_line(line: str) -> None:
#    """Parse a line and update counters and history."""
#    entry = parse(line)
#    if entry:
#        counts[entry["level"]] += 1
#        history.append(entry)

def process_line(line: str):
    """Parse a line and update counters and history."""
    entry = parse(line)

    if entry:
        counts[entry["level"]] += 1
        history.append(entry)

    return entry

def report() -> None:
    """Print level counts and the three most recent errors."""
    recent = [e for e in history if e["level"] == "ERROR"][-3:]
    click.echo(f"counts={dict(counts)}")
    for entry in recent:
        click.echo(f"  {entry['ts']} {entry['msg']}")


@click.command()
@click.argument("logfile", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--report-every", default=10, show_default=True, help="Seconds between reports.")
@click.option(
    "--error-threshold",
    default=5,
    type=click.IntRange(min=1),
    show_default=True,
    help="Number of errors before displaying an alert.",
)

def watch(logfile, report_every, error_threshold):
    """Follow LOGFILE and periodically report level counts and recent errors."""
    last_report = time.monotonic()
    errors_seen = 0
    error_alerted = False
    with logfile.open() as f:
        f.seek(0, 2)  # start at the end, like tail -f
        while True:
            line = f.readline()
            if line:
                entry = process_line(line.rstrip("\n"))

                if entry and entry["level"] == "ERROR":
                    errors_seen += 1

                    if errors_seen >= error_threshold and not error_alerted:
                        click.echo(f"ALERT: Error threshold reached "f"({errors_seen} errors).")
                        error_alerted = True
            else:
                time.sleep(0.1)

            if time.monotonic() - last_report >= report_every:
                last_report = time.monotonic()
                report()


if __name__ == "__main__":
    watch()