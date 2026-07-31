"""Generate dated prompts before each active SamOS reminder is due."""

from datetime import date, timedelta
from pathlib import Path

from validate_config import load_yaml, validate_reminder_profiles, validate_reminders


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "Dashboard" / "Reminders.md"
CALENDAR_OUTPUT = ROOT / "Dashboard" / "Reminders.ics"


def build_reminder_schedule(profiles: dict, items: dict, today: date | None = None) -> str:
    today = today or date.today()
    scheduled = []
    for item in items["reminders"]:
        if item["status"] != "active":
            continue
        offsets = profiles["profiles"][item["category"]]["reminder_days_before"]
        for offset in offsets:
            reminder_date = item["due"] - timedelta(days=offset)
            if reminder_date >= today:
                scheduled.append((reminder_date, item["due"], offset, item["title"]))
    scheduled.sort(key=lambda entry: (entry[0], entry[1], entry[3]))

    lines = ["# SamOS Reminders", "", f"**Generated:** {today:%B %d, %Y}", ""]
    if not scheduled:
        lines.append("No upcoming reminders are currently configured.")
    for reminder_date, due, offset, title in scheduled:
        timing = "due today" if offset == 0 else f"due in {offset} day{'s' if offset != 1 else ''}"
        lines.append(f"- **{reminder_date:%Y-%m-%d}:** {title} ({timing}; due {due:%Y-%m-%d})")
    return "\n".join(lines) + "\n"


def escape_ics(text: str) -> str:
    return text.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def build_reminder_calendar(profiles: dict, items: dict) -> str:
    """Create one all-day calendar entry for every configured reminder prompt."""
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//SamOS//Reminders//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "X-WR-CALNAME:SamOS Reminders",
    ]
    for item in items["reminders"]:
        if item["status"] != "active":
            continue
        offsets = profiles["profiles"][item["category"]]["reminder_days_before"]
        for offset in offsets:
            reminder_date = item["due"] - timedelta(days=offset)
            end_date = reminder_date + timedelta(days=1)
            timing = "Due today" if offset == 0 else f"Due in {offset} day{'s' if offset != 1 else ''}"
            lines.extend([
                "BEGIN:VEVENT",
                f"UID:{item['id']}-{offset}@samos-reminders",
                "DTSTAMP:20000101T000000Z",
                f"DTSTART;VALUE=DATE:{reminder_date:%Y%m%d}",
                f"DTEND;VALUE=DATE:{end_date:%Y%m%d}",
                f"SUMMARY:{escape_ics('Reminder: ' + item['title'])}",
                f"DESCRIPTION:{escape_ics(timing + ' - due ' + item['due'].isoformat())}",
                "TRANSP:TRANSPARENT",
                "END:VEVENT",
            ])
    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"


def main() -> None:
    profiles = load_yaml("reminder_profiles.yaml")
    items = load_yaml("Reminders/reminders.yaml")
    validate_reminder_profiles(profiles)
    validate_reminders(items, set(profiles["profiles"]))
    OUTPUT.write_text(build_reminder_schedule(profiles, items), encoding="utf-8")
    CALENDAR_OUTPUT.write_bytes(build_reminder_calendar(profiles, items).encode("utf-8"))
    print(f"Reminder schedule created: {OUTPUT}")
    print(f"Reminder calendar created: {CALENDAR_OUTPUT}")


if __name__ == "__main__":
    main()
