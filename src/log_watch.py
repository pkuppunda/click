import re
import time
from collections import Counter
from pathlib import Path

import click


import json
import urllib.request
import urllib.error
from collections import deque

LINE_RE = re.compile(r"^(?P<ts>\S+ \S+) (?P<level>[A-Z]+) (?P<msg>.*)$")

counts: Counter = Counter()
history: list[dict] = []


# Error-spike detection configuration - for Future Implementation
ERROR_THRESHOLD = 5
ERROR_WINDOW_SECONDS = 60

# Stores timestamps of recent ERROR entries.
ERROR_TIMESTAMPS = deque()

# Telegram credentials: configure before enabling notifications - for Future Implementation
TELEGRAM_BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"
TELEGRAM_CHAT_ID = "YOUR_TELEGRAM_CHAT_ID"

# For Future Implementation
def detect_error_spike(
    threshold: int = ERROR_THRESHOLD,
    window_seconds: int = ERROR_WINDOW_SECONDS,
    now: float | None = None,
) -> bool:
    """Return True when the threshold is reached within the time window.

    Call this function once for each ERROR log entry when the
    feature is activated in the future.
    """
    if threshold < 1:
        raise ValueError("threshold must be at least 1")

    if window_seconds < 1:
        raise ValueError("window_seconds must be at least 1")

    current_time = time.monotonic() if now is None else now

    # Remove errors that are outside the configured time window.
    while (
        ERROR_TIMESTAMPS
        and current_time - ERROR_TIMESTAMPS[0] > window_seconds
    ):
        ERROR_TIMESTAMPS.popleft()

    # Record the timestamp of the current ERROR.
    ERROR_TIMESTAMPS.append(current_time)

    # Trigger only when the threshold is reached, not on every
    # subsequent error in the same burst.
    return len(ERROR_TIMESTAMPS) == threshold

# For Future Implementation
def send_telegram_notification(message: str) -> None:
    """Send a Telegram message using the Telegram Bot API.

    Requires a valid bot token and chat ID.
    This function is defined for future use and is not called yet.
    """
    if (
        not TELEGRAM_BOT_TOKEN
        or TELEGRAM_BOT_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN"
    ):
        raise ValueError("Configure TELEGRAM_BOT_TOKEN first")

    if (
        not TELEGRAM_CHAT_ID
        or TELEGRAM_CHAT_ID == "YOUR_TELEGRAM_CHAT_ID"
    ):
        raise ValueError("Configure TELEGRAM_CHAT_ID first")

    url = (
        f"https://api.telegram.org/bot"
        f"{TELEGRAM_BOT_TOKEN}/sendMessage"
    )

    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
    }

    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            result = json.loads(response.read().decode("utf-8"))

            if not result.get("ok"):
                raise RuntimeError(
                    "Telegram API rejected the notification"
                )

    except urllib.error.HTTPError as exc:
        raise RuntimeError(
            f"Telegram HTTP request failed with status {exc.code}"
        ) from None

    except urllib.error.URLError:
        raise RuntimeError(
            "Unable to connect to Telegram"
        ) from None


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
        if entry["level"] == "ERROR":
            # FUTURE IMPLEMENTATION:
            # Detect whether the error threshold has been reached.
            #if detect_error_spike():
                # Send a Telegram notification only when a spike is detected.
                #send_telegram_notification(
                    #f"LogWatcher alert: {ERROR_THRESHOLD} errors "
                    #f"detected within {ERROR_WINDOW_SECONDS} seconds.\n"
                    #f"Latest error: {entry['msg']}\n"
                    #f"Timestamp: {entry['ts']}"
                #)
            pass


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