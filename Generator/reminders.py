"""Generate dated prompts before each active SamOS reminder is due."""

from datetime import date, timedelta
from pathlib import Path

from planner import load_events
from study import build_score_prompts
from validate_config import (
    load_yaml,
    validate_reminder_profiles,
    validate_reminders,
    validate_study_plan,
)


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


def append_folded_line(lines: list[str], line: str, limit: int = 75) -> None:
    """Append one RFC 5545 content line, folding long UTF-8 values safely."""
    first = True
    while len(line.encode("utf-8")) > (limit if first else limit - 1):
        available = limit if first else limit - 1
        split = min(len(line), available)
        while len(line[:split].encode("utf-8")) > available:
            split -= 1
        while split > 0 and line[split - 1] in {" ", "\t"}:
            split -= 1
        lines.append(("" if first else " ") + line[:split])
        line = line[split:]
        first = False
    lines.append(("" if first else " ") + line)


def add_all_day_prompt(lines: list[str], uid: str, day: date, title: str,
                       description: str) -> None:
    lines.extend([
        "BEGIN:VEVENT",
        f"UID:{uid}@samos-reminders",
        "DTSTAMP:20000101T000000Z",
        f"DTSTART;VALUE=DATE:{day:%Y%m%d}",
        f"DTEND;VALUE=DATE:{day + timedelta(days=1):%Y%m%d}",
    ])
    append_folded_line(lines, f"SUMMARY:{escape_ics(title)}")
    append_folded_line(lines, f"DESCRIPTION:{escape_ics(description)}")
    lines.extend(["TRANSP:TRANSPARENT", "END:VEVENT"])


def build_reminder_calendar(profiles: dict, items: dict, study_plan: dict | None = None,
                            events: list[dict] | None = None) -> str:
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
            timing = "Due today" if offset == 0 else f"Due in {offset} day{'s' if offset != 1 else ''}"
            add_all_day_prompt(
                lines,
                f"{item['id']}-{offset}",
                reminder_date,
                "Reminder: " + item["title"],
                timing + " - due " + item["due"].isoformat(),
            )
    if study_plan:
        for prompt in build_score_prompts(study_plan, events or []):
            add_all_day_prompt(
                lines,
                prompt["id"],
                prompt["date"],
                prompt["title"],
                prompt["description"],
            )
    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"


def main() -> None:
    profiles = load_yaml("reminder_profiles.yaml")
    items = load_yaml("Reminders/reminders.yaml")
    study_plan = load_yaml("Study/plan.yaml")
    validate_reminder_profiles(profiles)
    validate_reminders(items, set(profiles["profiles"]))
    validate_study_plan(study_plan)
    OUTPUT.write_text(build_reminder_schedule(profiles, items), encoding="utf-8")
    CALENDAR_OUTPUT.write_bytes(
        build_reminder_calendar(profiles, items, study_plan, load_events()).encode("utf-8")
    )
    print(f"Reminder schedule created: {OUTPUT}")
    print(f"Reminder calendar created: {CALENDAR_OUTPUT}")


if __name__ == "__main__":
    main()
