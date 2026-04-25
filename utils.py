"""
Utility helpers for Git Digest.
"""

from datetime import datetime


def format_date(iso_string: str) -> str:
    """Convert ISO 8601 date string to a human-readable format."""
    dt = datetime.fromisoformat(iso_string.replace("Z", "+00:00"))
    return dt.strftime("%d %b %Y, %H:%M UTC")


def time_ago(iso_string: str) -> str:
    """Return a relative time string like '3 days ago'."""
    dt = datetime.fromisoformat(iso_string.replace("Z", "+00:00"))
    now = datetime.now(dt.tzinfo)
    diff = now - dt
    seconds = int(diff.total_seconds())
    if seconds < 60:
        return f"{seconds}s ago"
    if seconds < 3600:
        return f"{seconds // 60}m ago"
    if seconds < 86400:
        return f"{seconds // 3600}h ago"
    return f"{diff.days}d ago"


def truncate(text: str, max_len: int = 72) -> str:
    """Truncate text to max_len characters, appending ellipsis if needed."""
    return text if len(text) <= max_len else text[:max_len - 1] + "…"
