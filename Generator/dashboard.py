"""Generate the read-only SamOS command-center dashboard."""

from datetime import date, timedelta
from html import escape
from pathlib import Path
from urllib.parse import quote

from planner import events_on, load_events, schedule_training, start_of_week
from study import (
    build_study_schedule,
    current_or_next_week,
    score_phase_for_day,
    score_target_for_day,
    study_assignments_for_week,
)
from validate_config import load_yaml


ROOT = Path(__file__).resolve().parents[1]
MARKDOWN_OUTPUT = ROOT / "Dashboard" / "Home.md"
HTML_OUTPUT = ROOT / "public" / "dashboard.html"


def percentage(value: int, total: int) -> int:
    return min(100, round(100 * value / total)) if total else 0


def assigned_twis_modules(plan: dict) -> int:
    return sum(
        len(week["twis"])
        for week in plan["weeks"]
        if not week["topic"].startswith("OFF")
    )


def assigned_review_weeks(plan: dict) -> int:
    return sum(not week["topic"].startswith("OFF") for week in plan["weeks"])


def daily_progress(progress: dict, day: date) -> dict:
    return next(
        (entry for entry in progress["daily"] if entry["date"] == day),
        {"date": day, "score_questions_completed": 0, "anki_completed": False},
    )


def weekly_progress(progress: dict, week_of: date) -> dict:
    return next(
        (entry for entry in progress["weeks"] if entry["week_of"] == week_of),
        {
            "week_of": week_of,
            "twis_completed": [],
            "anatomy_review_completed": False,
            "operation_review_completed": False,
            "case_review_completed": False,
        },
    )


def score_progress(plan: dict, progress: dict) -> tuple[int, int]:
    totals = {"full_pass": 0, "focused_review": 0}
    for entry in progress["daily"]:
        phase = score_phase_for_day(plan, entry["date"])["key"]
        totals[phase] += entry["score_questions_completed"]
    return totals["full_pass"], totals["focused_review"]


def completed_twis_modules(plan: dict, progress: dict) -> int:
    assigned = {
        week["week_of"]: set(week["twis"])
        for week in plan["weeks"]
        if not week["topic"].startswith("OFF")
    }
    return sum(
        len(set(entry["twis_completed"]) & assigned.get(entry["week_of"], set()))
        for entry in progress["weeks"]
    )


def completed_weekly_reviews(plan: dict, progress: dict, field: str) -> int:
    assigned = {
        week["week_of"]
        for week in plan["weeks"]
        if not week["topic"].startswith("OFF")
    }
    return sum(bool(entry[field]) for entry in progress["weeks"] if entry["week_of"] in assigned)


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
    study_week, study_week_label = current_or_next_week(plan, today)
    study_assignments = (
        study_assignments_for_week(plan, study_week, events)
        if study_week else {}
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
        "study_week": study_week,
        "study_week_label": study_week_label,
        "study_assignments": study_assignments,
    }


def build_markdown(context: dict, today: date) -> str:
    plan = context["plan"]
    progress = context["progress"]
    goals = plan["goals"]
    full_total = goals["score_full_pass_questions"]
    focused_total = goals["score_focused_review_questions"]
    full_targets = plan["daily_targets"]["full_pass"]
    focused_targets = plan["daily_targets"]["focused_review"]
    deep_day = plan["daily_targets"]["deep_study_day"].title()
    today_target = score_target_for_day(plan, today, context["events"])
    today_log = daily_progress(progress, today)
    full_complete, focused_complete = score_progress(plan, progress)
    twis_complete = completed_twis_modules(plan, progress)
    twis_total = assigned_twis_modules(plan)
    case_complete = completed_weekly_reviews(plan, progress, "case_review_completed")
    review_total = assigned_review_weeks(plan)
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
        week_log = weekly_progress(progress, week["week_of"])
        completed_modules = set(week_log["twis_completed"])
        assignments = context["study_assignments"]
        today_assignment = assignments.get(today, {"twis": [], "reviews": []})
        module_days = {
            module: day.strftime("%a")
            for day, assignment in assignments.items()
            for module in assignment["twis"]
        }
        score_target = today_target["questions"] if today_target else 0
        score_done = today_target is not None and today_log["score_questions_completed"] >= score_target
        lines.extend([
            f"- **{context['study_week_label']}:** {week['topic']}",
            "- **Today's checklist:**",
            f"  - [{'x' if score_done else ' '}] SCORE: "
            f"{today_log['score_questions_completed']}/{score_target} questions",
            f"  - [{'x' if today_log['anki_completed'] else ' '}] Anki: "
            f"{plan['daily_targets']['anki_minutes']} minutes",
            *(f"  - [{'x' if module in completed_modules else ' '}] TWIS: {module}"
              for module in today_assignment["twis"]),
            *(f"  - [{'x' if week_log[review['progress_field']] else ' '}] "
              f"{review['label']}: {review['detail']}"
              for review in today_assignment["reviews"]),
            "- **TWIS modules this week:**",
            *(f"  - [{'x' if module in completed_modules else ' '}] "
              f"{module_days.get(module, '—')} — {module}" for module in week["twis"]),
            "- [Open SCORE](https://www.surgicalcore.org/)",
            f"- [{'x' if week_log['anatomy_review_completed'] else ' '}] "
            f"**Anatomy review:** {week['anatomy']}",
            f"- [{'x' if week_log['operation_review_completed'] else ' '}] "
            f"**Operation review:** {week['operation']}",
            f"- [{'x' if week_log['case_review_completed'] else ' '}] "
            f"**Case review:** {week['case_review']}",
        ])
    lines.extend([
        f"- SCORE full question bank: `{progress_bar(full_complete, full_total)}` "
        f"{full_complete}/{full_total}",
        f"- SCORE focused review: `{progress_bar(focused_complete, focused_total)}` "
        f"{focused_complete}/{focused_total} maximum",
        f"- TWIS modules: `{progress_bar(twis_complete, twis_total)}` "
        f"{twis_complete}/{twis_total}",
        f"- Case reviews: {case_complete}/{review_total}",
        f"- Full-pass plan through {goals['score_full_pass_due']:%B %d}: "
        f"**{full_targets['weekday_score_questions']}/day; "
        f"{full_targets['deep_study_score_questions']} on {deep_day}**",
        f"- Focused review from {goals['score_focused_review_start']:%B %d} through "
        f"{goals['score_focused_review_due']:%B %d}: "
        f"**{focused_targets['weekday_score_questions']}/day; "
        f"{focused_targets['deep_study_score_questions']} on {deep_day}; stop when the flagged queue is complete**",
    ])
    if today_target:
        lines.append(
            f"- Today's scheduled SCORE target: **{today_target['questions']} questions** "
            f"({today_target['phase']['label'].lower()})"
        )
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
    full_total = goals["score_full_pass_questions"]
    focused_total = goals["score_focused_review_questions"]
    full_targets = plan["daily_targets"]["full_pass"]
    focused_targets = plan["daily_targets"]["focused_review"]
    deep_day = plan["daily_targets"]["deep_study_day"].title()
    today_target = score_target_for_day(plan, today, context["events"])
    today_log = daily_progress(progress, today)
    full_complete, focused_complete = score_progress(plan, progress)
    twis_complete = completed_twis_modules(plan, progress)
    case_complete = completed_weekly_reviews(plan, progress, "case_review_completed")
    review_total = assigned_review_weeks(plan)
    target_text = (
        f"SCORE today: {today_log['score_questions_completed']} / "
        f"{today_target['questions']} questions ({today_target['phase']['label'].lower()})"
        if today_target else "No SCORE questions scheduled today"
    )
    twis_total = assigned_twis_modules(plan)
    today_items = [event["title"] for event in events_on(today, context["events"])]
    today_items.extend(activity_summary(activity) for activity in context["schedule"].get(today, []))
    week = context["study_week"]
    week_label = context["study_week_label"]
    week_log = weekly_progress(progress, week["week_of"]) if week else None
    assignments = context["study_assignments"]
    today_assignment = assignments.get(today, {"twis": [], "reviews": []})
    module_days = {
        module: day.strftime("%a")
        for day, assignment in assignments.items()
        for module in assignment["twis"]
    }

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
    module_html = (
        render_list(
            [
                ("✓ " if module in set(week_log["twis_completed"]) else "☐ ")
                + f"{module_days.get(module, '—')} · {module}"
                for module in week["twis"]
            ],
            "No assigned modules",
        )
        if week else ""
    )
    score_checked = bool(
        today_target
        and today_log["score_questions_completed"] >= today_target["questions"]
    )
    today_study_checks = (
        "".join(
            f'<p><strong>{"✓" if module in set(week_log["twis_completed"]) else "☐"} TWIS:</strong> '
            f'{escape(module)}</p>'
            for module in today_assignment["twis"]
        )
        + "".join(
            f'<p><strong>{"✓" if week_log[review["progress_field"]] else "☐"} '
            f'{escape(review["label"])}:</strong> {escape(review["detail"])}</p>'
            for review in today_assignment["reviews"]
        )
        if week else ""
    )
    topic_html = (
        f'<p class="eyebrow">{escape(week_label)}</p><h2>{escape(week["topic"])}</h2>'
        f'<div class="today-checks"><p><strong>{"✓" if score_checked else "☐"} SCORE:</strong> '
        f'{today_log["score_questions_completed"]} / {today_target["questions"] if today_target else 0} questions</p>'
        f'<p><strong>{"✓" if today_log["anki_completed"] else "☐"} Anki:</strong> '
        f'{plan["daily_targets"]["anki_minutes"]} minutes; create up to '
        f'{plan["daily_targets"]["anki_new_cards_cap"]} cards from missed or guessed questions.</p>'
        f'{today_study_checks}</div>'
        f'<div class="module-block"><strong>TWIS modules this week</strong>{module_html}'
        f'<a class="score-link" href="https://www.surgicalcore.org/" target="_blank" rel="noopener">Open SCORE</a></div>'
        f'<p class="check"><strong>{"✓" if week_log["anatomy_review_completed"] else "☐"} Anatomy review:</strong> {escape(week["anatomy"])}</p>'
        f'<p class="check"><strong>{"✓" if week_log["operation_review_completed"] else "☐"} Operation review:</strong> {escape(week["operation"])}</p>'
        f'<p class="check"><strong>{"✓" if week_log["case_review_completed"] else "☐"} Case review:</strong> {escape(week["case_review"])}</p>'
        if week else '<h2>Study plan starts August 3</h2>'
    )

    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>SamOS Dashboard</title><style>
:root{{--navy:#07152f;--blue:#246bfe;--violet:#7c4dff;--ink:#15213a;--muted:#66708a;--line:#dfe6f4;--panel:#fff;--wash:#f4f7ff}}
*{{box-sizing:border-box}} body{{margin:0;background:linear-gradient(145deg,#eef4ff,#f6f0ff);color:var(--ink);font:15px/1.5 Inter,ui-sans-serif,system-ui,-apple-system,sans-serif}}
.shell{{max-width:1180px;margin:auto;padding:34px 22px 60px}} header{{background:linear-gradient(120deg,var(--navy),#163d86 62%,#5031a5);color:white;border-radius:24px;padding:30px;box-shadow:0 20px 60px #1d3f7926}}
header p{{margin:4px 0 0;color:#d9e5ff}} h1{{margin:0;font-size:clamp(30px,5vw,52px);letter-spacing:-.04em}} h2{{margin:0 0 12px;font-size:22px;letter-spacing:-.02em}} .date{{font-weight:700;color:#a9c8ff;text-transform:uppercase;letter-spacing:.12em;font-size:12px}}
.grid{{display:grid;grid-template-columns:repeat(12,1fr);gap:18px;margin-top:18px}} .card{{grid-column:span 6;background:var(--panel);border:1px solid #fff;border-radius:20px;padding:22px;box-shadow:0 10px 35px #263b6814}} .today-card{{grid-column:span 4}} .study-card{{grid-column:span 8}} .wide{{grid-column:span 12}} .third{{grid-column:span 4}}
.eyebrow{{color:var(--violet);font-size:12px;font-weight:800;letter-spacing:.12em;text-transform:uppercase;margin:0 0 8px}} ul{{padding-left:19px;margin:10px 0 0}} li{{margin:6px 0}} .muted{{color:var(--muted)}}
.metrics{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}} .metric{{background:var(--wash);border-radius:15px;padding:15px}} .metric-label{{font-size:12px;color:var(--muted);font-weight:700}} .metric-value{{font-size:25px;font-weight:850;margin:7px 0}} .metric-value span{{font-size:13px;color:var(--muted)}} .track{{height:7px;border-radius:8px;background:#dde5f7;overflow:hidden}} .fill{{height:100%;background:linear-gradient(90deg,var(--blue),var(--violet))}} .metric-pct{{font-size:11px;color:var(--muted);margin-top:5px}}
.module-block{{background:var(--wash);border-radius:14px;padding:13px 15px;margin:14px 0}} .module-block ul{{columns:2;column-gap:28px}} .module-block li{{break-inside:avoid}} .score-link{{display:inline-block;margin-top:12px;font-weight:800;text-decoration:none}} .today-checks{{border-left:3px solid var(--violet);padding-left:12px;margin:14px 0}} .today-checks p{{margin:5px 0}} .check{{margin:9px 0}} .pace{{display:block;width:fit-content;max-width:100%;background:#e9efff;color:#214ca0;border-radius:18px;padding:8px 12px;font-weight:800;margin-top:10px;overflow-wrap:anywhere}} .week{{display:grid;grid-template-columns:repeat(7,1fr);gap:8px}} .day{{background:var(--wash);border-radius:13px;padding:12px;min-width:0}} .day strong{{display:flex;justify-content:space-between}} .day strong span{{color:var(--muted);font-size:11px}} .day ul{{padding-left:15px;font-size:12px}} .notice{{margin-top:18px;border-left:4px solid var(--violet);background:#f0ebff;padding:13px 15px;border-radius:9px;color:#4c3389}} a{{color:#275fd3}}
@media(max-width:850px){{.card,.today-card,.study-card,.third{{grid-column:span 12}}.metrics{{grid-template-columns:repeat(2,1fr)}}.week{{grid-template-columns:1fr}}.module-block ul{{columns:1}}}}
</style></head><body><main class="shell">
<header><div class="date">{today:%A · %B %d, %Y}</div><h1>SamOS Dashboard</h1><p>One glance. The next good decision.</p></header>
{provisional}
<section class="grid">
<article class="card today-card"><p class="eyebrow">Today</p><h2>Your command list</h2>{render_list(today_items)}</article>
<article class="card study-card">{topic_html}<div class="pace">{escape(target_text)}</div>
<p class="muted">Full pass: {full_targets['weekday_score_questions']}/day, {full_targets['deep_study_score_questions']} on {deep_day}, through {goals['score_full_pass_due']:%b %d}. Focused review: {focused_targets['weekday_score_questions']}/day, {focused_targets['deep_study_score_questions']} on {deep_day}, through {goals['score_focused_review_due']:%b %d}; stop when the flagged queue is complete.</p></article>
<article class="card wide"><p class="eyebrow">Progress</p><div class="metrics">
{metric_card('SCORE · Full bank', full_complete, full_total)}
{metric_card('SCORE · Focused review cap', focused_complete, focused_total)}
{metric_card('TWIS modules', twis_complete, twis_total)}
{metric_card('Case reviews', case_complete, review_total)}
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
