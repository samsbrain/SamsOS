"""Build the public SamOS calendar feed from safe scheduling data."""

from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from planner import load_events, schedule_training, start_of_week
from validate_config import load_yaml, validate_cases, validate_master


ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "public"


def escape_ics(text: str) -> str:
    return text.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def add_all_day(lines: list[str], uid: str, title: str, start: date, end_inclusive: date) -> None:
    lines.extend([
        "BEGIN:VEVENT",
        f"UID:{uid}@samos",
        "DTSTAMP:20000101T000000Z",
        f"DTSTART;VALUE=DATE:{start:%Y%m%d}",
        f"DTEND;VALUE=DATE:{end_inclusive + timedelta(days=1):%Y%m%d}",
        f"SUMMARY:{escape_ics(title)}",
        "TRANSP:TRANSPARENT",
        "END:VEVENT",
    ])


def add_timed(lines: list[str], uid: str, title: str, day: date, start_time: str,
              duration_minutes: int, timezone_name: str, location: str = "",
              floating_times: bool = False) -> None:
    hour, minute = (int(part) for part in start_time.split(":"))
    local_timezone = ZoneInfo(timezone_name)
    start = datetime.combine(day, datetime.min.time(), local_timezone).replace(hour=hour, minute=minute)
    end = start + timedelta(minutes=duration_minutes)
    start_utc = start.astimezone(timezone.utc)
    end_utc = end.astimezone(timezone.utc)
    if floating_times:
        start_line = f"DTSTART:{start:%Y%m%dT%H%M%S}"
        end_line = f"DTEND:{end:%Y%m%dT%H%M%S}"
    else:
        start_line = f"DTSTART:{start_utc:%Y%m%dT%H%M%SZ}"
        end_line = f"DTEND:{end_utc:%Y%m%dT%H%M%SZ}"
    lines.extend([
        "BEGIN:VEVENT",
        f"UID:{uid}@samos",
        "DTSTAMP:20000101T000000Z",
        start_line,
        end_line,
        f"SUMMARY:{escape_ics(title)}",
        f"LOCATION:{escape_ics(location)}",
        "END:VEVENT",
    ])


def load_cases() -> list[dict]:
    cases = []
    for path in sorted((ROOT / "Cases").glob("????-??-??.yaml")):
        data = load_yaml(str(path.relative_to(ROOT)))
        validate_cases(data, path.stem)
        cases.extend(data["cases"])
    return cases


def build_calendar(data: dict, today: date | None = None, *, floating_times: bool = False,
                   calendar_name: str = "SamOS") -> str:
    today = today or date.today()
    end = today + timedelta(days=data["preferences"]["calendar_horizon_days"])
    timezone_name = data["person"]["timezone"]
    events = load_events()
    lines = [
        "BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//SamOS//Calendar//EN",
        "CALSCALE:GREGORIAN", "METHOD:PUBLISH", f"X-WR-CALNAME:{calendar_name}",
    ]

    for event in events:
        if event["end"] >= today and event["start"] <= end:
            add_all_day(lines, event["id"], event["title"], event["start"], event["end"])

    first_week = start_of_week(today, data["preferences"]["week_starts_on"])
    week = first_week
    while week <= end:
        dates = [week + timedelta(days=offset) for offset in range(7)]
        schedule, _ = schedule_training(data, dates, events)
        for day, activities in schedule.items():
            if day < today or day > end:
                continue
            for activity in activities:
                uid = f"{activity['id']}-{day:%Y%m%d}"
                if "start_time" in activity:
                    add_timed(lines, uid, activity["title"], day, activity["start_time"],
                              activity["duration_minutes"], timezone_name, activity.get("location", ""),
                              floating_times)
                else:
                    add_all_day(lines, uid, activity["title"], day, day)
        week += timedelta(days=7)

    for case in load_cases():
        if today <= case["date"] <= end:
            add_timed(lines, f"case-{case['id']}", case["procedure"], case["date"],
                      case["start_time"], case["duration_minutes"], timezone_name,
                      case.get("location", ""), floating_times)

    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"


def main() -> None:
    data = load_yaml("master.yaml")
    validate_master(data)
    PUBLIC.mkdir(exist_ok=True)
    output = PUBLIC / "SamOS.ics"
    output.write_bytes(build_calendar(data).encode("utf-8"))
    print(f"Public calendar created: {output}")
    compatibility_output = PUBLIC / "calendar.ics"
    compatibility_output.write_bytes(build_calendar(
        data,
        floating_times=True,
        calendar_name="SamOS Residency Calendar",
    ).encode("utf-8"))
    print(f"Apple compatibility calendar created: {compatibility_output}")


if __name__ == "__main__":
    main()
