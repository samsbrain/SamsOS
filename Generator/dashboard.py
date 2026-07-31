"""Generate the read-only SamOS command-center dashboard."""

from datetime import date, timedelta
from html import escape
from pathlib import Path
from urllib.parse import quote

from planner import events_on, load_events, schedule_training, start_of_week
from study import build_study_schedule, week_for_day
from validate_config import load_yaml


ROOT = Path(__file__).resolve().parents[1]
MARKDOWN_OUTPUT = ROOT / "Dashboard" / "Home.md"
HTML_OUTPUT = ROOT / "public" / "dashboard.html"


def percentage(value: int, total: int) -> int:
    return round(100 * value / total) if total else 0


def assigned_twis_weeks(plan: dict) -> int:
    return sum(not week["topic"].startswith("OFF") for week in plan["weeks"])


def progress_bar(value: int, total: int, width: int = 16) -> str:
    complete = min(width, round(width * value / total)) if total else 0
    return "█" * complete + "░" * (width - complete)


def activity_summary(activity: dict) -> str:
    details = [f"{activity['duration_minutes']} min"]
    if activity.get("start_time"):
        details.insert(0, activity["start_time"])
    return f"{activity['title']} ({' · '.join(details)})"


def collect_context(today: date) -> dict:
    master = load_yaml("master.yaml")
    plan = load_yaml("Study/plan.yaml")
    progress = load_yaml("Study/progress.yaml")
    reminders = load_yaml("Reminders/reminders.yaml")["reminders"]
    events = load_events()

    week_start = start_of_week(today, master["preferences"]["week_starts_on"])
    dates = [week_start + timedelta(days=offset) for offset in range(7)]
    schedule, warnings = schedule_training(master, dates, events)
    study_schedule = build_study_schedule(plan, dates, events)
    for day in dates:
        schedule[day].extend(study_schedule[day])

    active_reminders = sorted(
        (item for item in reminders if item["status"] == "active" and item["due"] >= today),
        key=lambda item: item["due"],
    )
    upcoming_events = sorted(
        (
            event for event in events
            if event["end"] >= today and event["start"] <= today + timedelta(days=14)
        ),
        key=lambda event: (event["start"], event["title"]),
    )
    finance_files = sorted(
        path for path in (ROOT / "Finance").iterdir()
        if path.suffix.lower() in {".xlsx", ".xls", ".csv", ".tsv"}
    )
    return {
        "master": master,
        "plan": plan,
        "progress": progress,
        "events": events,
        "schedule": schedule,
        "dates": dates,
        "warnings": warnings,
        "active_reminders": active_reminders,
        "upcoming_events": upcoming_events,
        "finance_files": finance_files,
        "study_week": week_for_day(plan, today),
    }


def build_markdown(context: dict, today: date) -> str:
    plan = context["plan"]
    progress = context["progress"]
    goals = plan["goals"]
    score_total = goals["score_questions_per_pass"]
    combined_complete = progress["score"]["pass_1_completed"] + progress["score"]["pass_2_completed"]
    combined_total = score_total * goals["score_passes"]
    days_left = max((goals["score_pass_2_due"] - today).days + 1, 1)
    daily_pace = max(0, -(-(combined_total - combined_complete) // days_left))
    twis_total = assigned_twis_weeks(plan)
    today_events = events_on(today, context["events"])
    today_activities = context["schedule"].get(today, [])

    lines = [
        "# SamOS Dashboard", "",
        f"**Today:** {today:%A, %B %d, %Y}", "",
        "> Read-only command center. Tell Codex what changed; generated files remain outputs.", "",
        "## Today", "",
    ]
    lines.extend(f"- **{event['title']}** ({event['type']})" for event in today_events)
    lines.extend(f"- [ ] {activity_summary(activity)}" for activity in today_activities)
    if not today_events and not today_activities:
        lines.append("- No scheduled items")

    lines.extend(["", "## Study command center", ""])
    if context["study_week"]:
        week = context["study_week"]
        lines.extend([
            f"- **Weekly topic:** {week['topic']}",
            f"- **Operation:** {week['operation']}",
            f"- **Case review:** {week['case_review']}",
        ])
    lines.extend([
        f"- SCORE Pass 1: `{progress_bar(progress['score']['pass_1_completed'], score_total)}` "
        f"{progress['score']['pass_1_completed']}/{score_total}",
        f"- SCORE Pass 2: `{progress_bar(progress['score']['pass_2_completed'], score_total)}` "
        f"{progress['score']['pass_2_completed']}/{score_total}",
        f"- TWIS weeks: `{progress_bar(progress['twis']['weeks_completed'], twis_total)}` "
        f"{progress['twis']['weeks_completed']}/{twis_total}",
        f"- Case reviews: {progress['reviews']['cases_completed']}/{len(plan['weeks'])}",
        f"- Required average through November 30: **{daily_pace} SCORE questions/day**",
    ])
    if plan.get("source_status") == "provisional":
        lines.extend(["", f"> **Curriculum note:** {plan['source_note']}"])

    lines.extend(["", "## This week", ""])
    for day in context["dates"]:
        day_items = [event["title"] for event in events_on(day, context["events"])]
        day_items.extend(activity["title"] for activity in context["schedule"][day])
        lines.append(f"- **{day:%a %m/%d}:** " + ("; ".join(day_items) if day_items else "Open"))

    lines.extend(["", "## Upcoming reminders", ""])
    lines.extend(
        f"- **{item['due']:%b %d}:** {item['title']}"
        for item in context["active_reminders"][:8]
    )

    lines.extend(["", "## Finance", ""])
    if context["finance_files"]:
        lines.extend(f"- [{path.name}](../Finance/{path.name})" for path in context["finance_files"])
    else:
        lines.append("- No worksheets linked yet; add prior Excel files to `Finance/` when ready.")
    lines.extend(["", f"_Study progress last updated: {progress['last_updated']:%B %d, %Y}_", ""])
    return "\n".join(lines)


def render_list(items: list[str], empty: str = "Nothing scheduled") -> str:
    if not items:
        return f'<p class="muted">{escape(empty)}</p>'
    return "<ul>" + "".join(f"<li>{escape(item)}</li>" for item in items) + "</ul>"


def metric_card(label: str, value: int, total: int) -> str:
    pct = percentage(value, total)
    return (
        '<div class="metric">'
        f'<div class="metric-label">{escape(label)}</div>'
        f'<div class="metric-value">{value:,}<span> / {total:,}</span></div>'
        f'<div class="track"><div class="fill" style="width:{pct}%"></div></div>'
        f'<div class="metric-pct">{pct}%</div></div>'
    )


def build_html(context: dict, today: date) -> str:
    plan = context["plan"]
    progress = context["progress"]
    goals = plan["goals"]
    score_total = goals["score_questions_per_pass"]
    combined_complete = progress["score"]["pass_1_completed"] + progress["score"]["pass_2_completed"]
    combined_total = score_total * goals["score_passes"]
    days_left = max((goals["score_pass_2_due"] - today).days + 1, 1)
    pace = max(0, -(-(combined_total - combined_complete) // days_left))
    twis_total = assigned_twis_weeks(plan)
    today_items = [event["title"] for event in events_on(today, context["events"])]
    today_items.extend(activity_summary(activity) for activity in context["schedule"].get(today, []))
    week = context["study_week"]

    week_rows = "".join(
        f'<div class="day"><strong>{day:%a}<span>{day:%m/%d}</span></strong>'
        + render_list(
            [event["title"] for event in events_on(day, context["events"])]
            + [activity["title"] for activity in context["schedule"][day]],
            "Open",
        ) + "</div>"
        for day in context["dates"]
    )
    reminder_items = [f"{item['due']:%b %d} — {item['title']}" for item in context["active_reminders"][:8]]
    event_items = [
        f"{event['start']:%b %d}" + (f"–{event['end']:%b %d}" if event["end"] != event["start"] else "")
        + f" — {event['title']}"
        for event in context["upcoming_events"]
    ]
    finance_links = "".join(
        f'<li><a href="https://github.com/samsbrain/SamsOS/blob/main/Finance/{quote(path.name)}">{escape(path.name)}</a></li>'
        for path in context["finance_files"]
    ) or '<li class="muted">No worksheets linked yet</li>'
    provisional = (
        f'<div class="notice"><strong>Curriculum migration in progress.</strong> {escape(plan["source_note"])}</div>'
        if plan.get("source_status") == "provisional" else ""
    )
    topic_html = (
        f'<p class="eyebrow">This week</p><h2>{escape(week["topic"])}</h2>'
        f'<p><strong>Operation:</strong> {escape(week["operation"])}</p>'
        f'<p><strong>Case:</strong> {escape(week["case_review"])}</p>'
        f'<p><strong>Anatomy:</strong> {escape(week["anatomy"])}</p>'
        if week else '<h2>Study plan starts August 3</h2>'
    )

    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>SamOS Dashboard</title><style>
:root{{--navy:#07152f;--blue:#246bfe;--violet:#7c4dff;--ink:#15213a;--muted:#66708a;--line:#dfe6f4;--panel:#fff;--wash:#f4f7ff}}
*{{box-sizing:border-box}} body{{margin:0;background:linear-gradient(145deg,#eef4ff,#f6f0ff);color:var(--ink);font:15px/1.5 Inter,ui-sans-serif,system-ui,-apple-system,sans-serif}}
.shell{{max-width:1180px;margin:auto;padding:34px 22px 60px}} header{{background:linear-gradient(120deg,var(--navy),#163d86 62%,#5031a5);color:white;border-radius:24px;padding:30px;box-shadow:0 20px 60px #1d3f7926}}
header p{{margin:4px 0 0;color:#d9e5ff}} h1{{margin:0;font-size:clamp(30px,5vw,52px);letter-spacing:-.04em}} h2{{margin:0 0 12px;font-size:22px;letter-spacing:-.02em}} .date{{font-weight:700;color:#a9c8ff;text-transform:uppercase;letter-spacing:.12em;font-size:12px}}
.grid{{display:grid;grid-template-columns:repeat(12,1fr);gap:18px;margin-top:18px}} .card{{grid-column:span 6;background:var(--panel);border:1px solid #fff;border-radius:20px;padding:22px;box-shadow:0 10px 35px #263b6814}} .wide{{grid-column:span 12}} .third{{grid-column:span 4}}
.eyebrow{{color:var(--violet);font-size:12px;font-weight:800;letter-spacing:.12em;text-transform:uppercase;margin:0 0 8px}} ul{{padding-left:19px;margin:10px 0 0}} li{{margin:6px 0}} .muted{{color:var(--muted)}}
.metrics{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}} .metric{{background:var(--wash);border-radius:15px;padding:15px}} .metric-label{{font-size:12px;color:var(--muted);font-weight:700}} .metric-value{{font-size:25px;font-weight:850;margin:7px 0}} .metric-value span{{font-size:13px;color:var(--muted)}} .track{{height:7px;border-radius:8px;background:#dde5f7;overflow:hidden}} .fill{{height:100%;background:linear-gradient(90deg,var(--blue),var(--violet))}} .metric-pct{{font-size:11px;color:var(--muted);margin-top:5px}}
.pace{{display:block;width:fit-content;max-width:100%;background:#e9efff;color:#214ca0;border-radius:18px;padding:8px 12px;font-weight:800;margin-top:10px;overflow-wrap:anywhere}} .week{{display:grid;grid-template-columns:repeat(7,1fr);gap:8px}} .day{{background:var(--wash);border-radius:13px;padding:12px;min-width:0}} .day strong{{display:flex;justify-content:space-between}} .day strong span{{color:var(--muted);font-size:11px}} .day ul{{padding-left:15px;font-size:12px}} .notice{{margin-top:18px;border-left:4px solid var(--violet);background:#f0ebff;padding:13px 15px;border-radius:9px;color:#4c3389}} a{{color:#275fd3}}
@media(max-width:850px){{.card,.third{{grid-column:span 12}}.metrics{{grid-template-columns:repeat(2,1fr)}}.week{{grid-template-columns:1fr}}}}
</style></head><body><main class="shell">
<header><div class="date">{today:%A · %B %d, %Y}</div><h1>SamOS Dashboard</h1><p>One glance. The next good decision.</p></header>
{provisional}
<section class="grid">
<article class="card"><p class="eyebrow">Today</p><h2>Your command list</h2>{render_list(today_items)}</article>
<article class="card">{topic_html}<div class="pace">Required SCORE pace: {pace} questions/day</div></article>
<article class="card wide"><p class="eyebrow">Progress</p><div class="metrics">
{metric_card('SCORE · Pass 1', progress['score']['pass_1_completed'], score_total)}
{metric_card('SCORE · Pass 2', progress['score']['pass_2_completed'], score_total)}
{metric_card('TWIS weeks', progress['twis']['weeks_completed'], twis_total)}
{metric_card('Case reviews', progress['reviews']['cases_completed'], len(plan['weeks']))}
</div></article>
<article class="card wide"><p class="eyebrow">This week</p><div class="week">{week_rows}</div></article>
<article class="card third"><p class="eyebrow">Coming up</p><h2>Events</h2>{render_list(event_items)}</article>
<article class="card third"><p class="eyebrow">Don't forget</p><h2>Reminders</h2>{render_list(reminder_items)}</article>
<article class="card third"><p class="eyebrow">Monthly review</p><h2>Finance files</h2><ul>{finance_links}</ul></article>
</section></main></body></html>'''


def main() -> None:
    today = date.today()
    context = collect_context(today)
    MARKDOWN_OUTPUT.parent.mkdir(exist_ok=True)
    HTML_OUTPUT.parent.mkdir(exist_ok=True)
    MARKDOWN_OUTPUT.write_text(build_markdown(context, today), encoding="utf-8")
    HTML_OUTPUT.write_text(build_html(context, today), encoding="utf-8")
    print(f"Dashboard created: {MARKDOWN_OUTPUT}")
    print(f"Public dashboard created: {HTML_OUTPUT}")


if __name__ == "__main__":
    main()
