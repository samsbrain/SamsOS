"""Build daily SCORE/TWIS assignments and one integrated case review per week."""

from datetime import date, timedelta


BLOCKING_EVENT_TYPES = {"call", "vacation"}


def events_on(day: date, events: list[dict]) -> list[dict]:
    return [event for event in events if event["start"] <= day <= event["end"]]


def week_for_day(plan: dict, day: date) -> dict | None:
    for week in plan["weeks"]:
        if week["week_of"] <= day <= week["week_of"] + timedelta(days=6):
            return week
    return None


def common_notes(week: dict, targets: dict) -> list[str]:
    return [
        f"Weekly topic: {week['topic']}",
        f"TWIS: {'; '.join(week['twis'])}",
        f"SCORE focus: {'; '.join(week['score_topics'])}",
        f"Anki: {targets['anki_minutes']} minutes; make up to 3 cards from missed or guessed questions",
        "Review explanations and record the management detail that changes the answer",
    ]


def build_study_schedule(plan: dict, dates: list[date], events: list[dict]) -> dict:
    """Return flexible all-day study activities adjusted for call and vacation."""
    schedule = {day: [] for day in dates}
    targets = plan["daily_targets"]
    deep_day = targets["deep_study_day"]
    case_day = targets["case_review_day"]

    for day in dates:
        if day < plan["start"] or day > plan["end"]:
            continue
        week = week_for_day(plan, day)
        if not week:
            continue

        day_events = events_on(day, events)
        is_call = any(event["type"] == "call" for event in day_events)
        is_vacation = any(event["type"] == "vacation" for event in day_events)
        is_post_call = any(
            event["type"] == "call"
            for event in events_on(day - timedelta(days=1), events)
        )
        weekday = day.strftime("%A").lower()

        if is_post_call:
            continue

        if weekday == case_day:
            notes = [
                f"Case: {week['case_review']}",
                f"Operation: {week['operation']}",
                f"Anatomy: {week['anatomy']}",
                f"Complication: {week['complication']}",
                "Answer: What do I do first? What changes management? When do I call for help?",
                "Capture one pearl, one uncertainty, and one follow-up topic",
            ]
            if is_vacation:
                notes.insert(0, "Vacation rule: optional; skip without catch-up guilt")
            if is_call:
                notes.insert(0, "Call-day rule: optional; patient care comes first")
            schedule[day].append({
                "id": f"weekly_case_review_{week['week_of']:%Y%m%d}",
                "title": f"Weekly case review: {week['case_review']}",
                "duration_minutes": 60,
                "notes": notes,
            })
            continue

        notes = common_notes(week, targets)
        if is_call:
            questions = targets["call_score_questions"]
            title = f"Optional study: {week['topic']}"
            duration = 15
            notes.insert(0, f"Call-day minimum: {questions} SCORE questions only if patient care allows")
        elif is_vacation:
            questions = targets["vacation_score_questions"]
            title = f"Light study: {week['topic']}"
            duration = 20
            notes.insert(0, f"Vacation target: {questions} SCORE questions, then enjoy the day")
        elif weekday == deep_day:
            questions = targets["deep_study_score_questions"]
            title = f"Deep study: {week['topic']}"
            duration = 120
            notes.insert(0, f"Weekend target: {questions} SCORE questions")
            notes.append(f"Preview this week's case: {week['case_review']}")
        else:
            questions = targets["weekday_score_questions"]
            title = f"Study: {week['topic']}"
            duration = 60
            notes.insert(0, f"Today's target: {questions} SCORE questions")

        schedule[day].append({
            "id": f"study_{week['week_of']:%Y%m%d}_{weekday}",
            "title": title,
            "duration_minutes": duration,
            "notes": notes,
        })
    return schedule
