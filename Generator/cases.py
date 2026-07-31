"""Cross-reference weekly cases with knowledge and create a calendar file."""

import argparse
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from validate_config import load_yaml, validate_cases, validate_knowledge


ROOT = Path(__file__).resolve().parents[1]
DASHBOARD = ROOT / "Dashboard"


def escape_ics(text: str) -> str:
    return text.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def match_topics(case: dict, topics: list[dict]) -> list[dict]:
    explicit = set(case.get("knowledge_topics", []))
    tags = set(case.get("tags", []))
    return [topic for topic in topics if topic["id"] in explicit or tags.intersection(topic["tags"])]


def build_case_brief(data: dict, knowledge: dict) -> str:
    lines = ["# Weekly Case Brief", "", f"**Week of:** {data['week_of']:%B %d, %Y}", ""]
    if not data["cases"]:
        lines.append("No cases are currently entered for this week.")
    for case in sorted(data["cases"], key=lambda item: (item["date"], item["start_time"])):
        lines.extend([f"## {case['date']:%A, %B %d} - {case['procedure']}", ""])
        lines.append(f"- Time: {case['start_time']}")
        if case.get("location"):
            lines.append(f"- Location: {case['location']}")
        matches = match_topics(case, knowledge["topics"])
        if matches:
            lines.append("- Related knowledge:")
            lines.extend(f"  - [{topic['title']}](../Knowledge/{topic['note']})" for topic in matches)
        else:
            lines.append("- Related knowledge: none indexed yet")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def build_calendar(data: dict, timezone_name: str) -> str:
    timezone = ZoneInfo(timezone_name)
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//SamOS//Weekly Cases//EN", "CALSCALE:GREGORIAN"]
    for case in data["cases"]:
        hour, minute = (int(part) for part in case["start_time"].split(":"))
        start = datetime.combine(case["date"], datetime.min.time(), timezone).replace(hour=hour, minute=minute)
        end = start + timedelta(minutes=case["duration_minutes"])
        lines.extend([
            "BEGIN:VEVENT",
            f"UID:{case['id']}@samos",
            f"DTSTAMP:{datetime.now(ZoneInfo('UTC')):%Y%m%dT%H%M%SZ}",
            f"DTSTART;TZID={timezone_name}:{start:%Y%m%dT%H%M%S}",
            f"DTEND;TZID={timezone_name}:{end:%Y%m%dT%H%M%S}",
            f"SUMMARY:{escape_ics(case['procedure'])}",
            f"LOCATION:{escape_ics(case.get('location', ''))}",
            "END:VEVENT",
        ])
    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a case brief and calendar.")
    parser.add_argument("week", help="Monday date in YYYY-MM-DD format")
    args = parser.parse_args()
    case_data = load_yaml(f"Cases/{args.week}.yaml")
    knowledge = load_yaml("Knowledge/index.yaml")
    master = load_yaml("master.yaml")
    validate_cases(case_data, args.week)
    validate_knowledge(knowledge)
    DASHBOARD.joinpath("CaseBrief.md").write_text(build_case_brief(case_data, knowledge), encoding="utf-8")
    DASHBOARD.joinpath("Cases.ics").write_text(build_calendar(case_data, master["person"]["timezone"]), encoding="utf-8")
    print("Case brief and calendar created.")


if __name__ == "__main__":
    main()
