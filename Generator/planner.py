"""Generate a weekly plan from SamOS configuration and dated events."""

import argparse
from datetime import date, timedelta
from pathlib import Path

from validate_config import load_yaml, validate_master, validate_month


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "Dashboard" / "WeeklyPlan.md"
PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2}
TRAINING_BLOCKING_EVENT_TYPES = {"call", "vacation"}


def start_of_week(today: date, week_starts_on: str) -> date:
    first_weekday = 0 if week_starts_on == "monday" else 6
    days_since_start = (today.weekday() - first_weekday) % 7
    return today - timedelta(days=days_since_start)


def load_events() -> list[dict]:
    """Load all dated events; monthly files stay small and human-editable."""
    events = []
    for path in sorted((ROOT / "Monthly").glob("????-??.yaml")):
        data = load_yaml(str(path.relative_to(ROOT)))
        validate_month(data, path.name)
        events.extend(data["events"])
    return events


def events_on(day: date, events: list[dict]) -> list[dict]:
    return [event for event in events if event["start"] <= day <= event["end"]]


def format_activity(activity: dict) -> str:
    details = []
    if "start_time" in activity:
        hour, minute = (int(part) for part in activity["start_time"].split(":"))
        suffix = "AM" if hour < 12 else "PM"
        details.append(f"{hour % 12 or 12}:{minute:02d} {suffix}")
    details.append(f"{activity['duration_minutes']} minutes")
    if "location" in activity:
        details.append(activity["location"])
    lines = [f"- [ ] {activity['title']} ({' / '.join(details)})"]
    lines.extend(f"  - {note}" for note in activity.get("notes", []))
    return "\n".join(lines)


def schedule_training(data: dict, dates: list[date], events: list[dict]) -> tuple[dict, list[str]]:
    """Protect fixed routines, place yoga, then fit weights into open days."""
    schedule = {day: [] for day in dates}
    blocked = {
        day
        for day in dates
        if any(event["type"] in TRAINING_BLOCKING_EVENT_TYPES for event in events_on(day, events))
    }

    for routine in data["routines"]:
        for day in dates:
            if day in blocked or day.strftime("%A").lower() not in routine["days"]:
                continue
            schedule[day].append(dict(routine))

    training = data["training_plan"]
    eligible = []
    for day in dates:
        activity_ids = {activity["id"] for activity in schedule[day]}
        if day in blocked:
            continue
        if training["avoid_bjj_days"] and "bjj_training" in activity_ids:
            continue
        if training["avoid_yoga_days"] and "yoga" in activity_ids:
            continue
        eligible.append(day)

    warnings = []
    sessions = training["sessions"]
    for session, day in zip(sessions, eligible):
        session_name = session["name"]
        schedule[day].append({
            "id": f"weight_training_{session_name.lower().replace(' ', '_')}",
            "title": f"Weight training: {session_name}",
            "duration_minutes": training["duration_minutes"],
            "notes": session.get("notes", []),
        })
    if len(eligible) < len(sessions):
        shortfall = len(sessions) - len(eligible)
        warnings.append(
            f"Could not place {shortfall} weight session(s) without conflicting with "
            "BJJ, yoga, call, or vacation."
        )
    return schedule, warnings


def build_weekly_plan(data: dict, events: list[dict], today: date | None = None) -> str:
    today = today or date.today()
    week_start = start_of_week(today, data["preferences"]["week_starts_on"])
    dates = [week_start + timedelta(days=offset) for offset in range(7)]
    schedule, warnings = schedule_training(data, dates, events)

    active_goals = [goal for goal in data["goals"] if goal["status"] == "active"]
    active_goals.sort(key=lambda goal: PRIORITY_ORDER[goal["priority"]])
    active_projects = [project for project in data["projects"] if project["status"] == "active"]
    lines = ["# SamOS Weekly Plan", "", f"**Week:** {dates[0]:%B %d, %Y} to {dates[-1]:%B %d, %Y}", ""]

    if warnings:
        lines.extend(["## Planning warnings", ""])
        lines.extend(f"- {warning}" for warning in warnings)
        lines.append("")

    lines.extend(["## Active goals", ""])
    lines.extend(f"- **{goal['title']}** - {goal['priority']} priority" for goal in active_goals)
    lines.extend(["", "## Project next actions", ""])
    lines.extend(f"- [ ] **{project['title']}:** {project['next_action']}" for project in active_projects)
    lines.extend(["", "## Daily plan", ""])

    for day in dates:
        lines.extend([f"### {day:%A, %B %d}", ""])
        day_events = events_on(day, events)
        lines.extend(f"- **{event['title']}** ({event['type']})" for event in day_events)
        lines.extend(format_activity(activity) for activity in schedule[day])
        if not day_events and not schedule[day]:
            lines.append("- No scheduled activities")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a SamOS weekly plan.")
    parser.add_argument("--week", type=date.fromisoformat, help="Any date in the desired week (YYYY-MM-DD)")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    data = load_yaml("master.yaml")
    validate_master(data)
    OUTPUT.write_text(build_weekly_plan(data, load_events(), args.week), encoding="utf-8")
    print(f"Weekly plan created: {OUTPUT}")


if __name__ == "__main__":
    main()
