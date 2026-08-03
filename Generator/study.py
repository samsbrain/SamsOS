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


def current_or_next_week(plan: dict, day: date) -> tuple[dict | None, str]:
    """Return the active study week, or the next one before the plan starts."""
    current = week_for_day(plan, day)
    if current:
        return current, "This week"
    upcoming = next((week for week in plan["weeks"] if week["week_of"] > day), None)
    if upcoming:
        start_label = upcoming["week_of"].strftime("%B %d").replace(" 0", " ")
        return upcoming, f"Starts {start_label}"
    return None, "Study plan complete"


def score_phase_for_day(plan: dict, day: date) -> dict:
    """Return the active SCORE phase and its daily target profile."""
    goals = plan["goals"]
    if day >= goals["score_focused_review_start"]:
        return {
            "key": "focused_review",
            "label": "Focused review",
            "targets": plan["daily_targets"]["focused_review"],
            "scope": goals["score_focused_review_scope"],
        }
    return {
        "key": "full_pass",
        "label": "Full question-bank pass",
        "targets": plan["daily_targets"]["full_pass"],
        "scope": "New SCORE questions with full explanation review",
    }


def score_target_for_day(plan: dict, day: date, events: list[dict]) -> dict | None:
    """Return the SCORE question target for one day, adjusted for recovery and travel."""
    if day < plan["start"] or day > plan["end"]:
        return None
    week = week_for_day(plan, day)
    if not week:
        return None

    daily = plan["daily_targets"]
    phase = score_phase_for_day(plan, day)
    targets = phase["targets"]
    day_events = events_on(day, events)
    is_call = any(event["type"] == "call" for event in day_events)
    is_vacation = any(event["type"] == "vacation" for event in day_events)
    is_post_call = any(
        event["type"] == "call"
        for event in events_on(day - timedelta(days=1), events)
    )
    weekday = day.strftime("%A").lower()

    if is_post_call:
        return {
            "questions": 0,
            "kind": "recovery",
            "title": "SCORE recovery day - 0 questions",
            "instruction": "Post-call recovery is protected; sleep and resume tomorrow without catch-up guilt",
            "phase": phase,
            "week": week,
        }

    phase_title = "SCORE full pass" if phase["key"] == "full_pass" else "Focused SCORE review"
    question_type = "new SCORE" if phase["key"] == "full_pass" else "missed, guessed, or weak-topic SCORE"
    if is_call:
        questions = targets["call_score_questions"]
        title = f"Optional {phase_title}: {questions} questions (call) - {week['topic']}"
        instruction = f"Only if patient care allows: {questions} {question_type} questions"
        kind = "call"
    elif is_vacation:
        questions = targets["vacation_score_questions"]
        title = f"{phase_title}: {questions} questions (vacation) - {week['topic']}"
        instruction = f"Vacation target: {questions} {question_type} questions, then enjoy the day"
        kind = "vacation"
    elif weekday == daily["deep_study_day"]:
        questions = targets["deep_study_score_questions"]
        title = f"{phase_title}: {questions} questions (deep study) - {week['topic']}"
        instruction = f"Weekend deep-study target: {questions} {question_type} questions"
        kind = "deep"
    else:
        questions = targets["weekday_score_questions"]
        title = f"{phase_title}: {questions} questions - {week['topic']}"
        instruction = f"Today's target: {questions} {question_type} questions"
        kind = "standard"

    return {
        "questions": questions,
        "kind": kind,
        "title": title,
        "instruction": instruction,
        "phase": phase,
        "week": week,
    }


def build_score_prompts(plan: dict, events: list[dict]) -> list[dict]:
    """Create one all-day SCORE prompt for every day in the study plan."""
    prompts = []
    day = plan["start"]
    targets = plan["daily_targets"]
    while day <= plan["end"]:
        target = score_target_for_day(plan, day, events)
        if target:
            week = target["week"]
            description = [
                target["instruction"],
                f"Phase: {target['phase']['label']}",
                f"Scope: {target['phase']['scope']}",
                f"Weekly topic: {week['topic']}",
            ]
            if target["questions"]:
                description.extend([
                    f"Modules: {'; '.join(week['twis'])}",
                    f"Anki: {targets['anki_minutes']} minutes; create up to "
                    f"{targets['anki_new_cards_cap']} cards from missed or guessed questions",
                    "Review explanations and capture the management detail that changes the answer",
                ])
            prompts.append({
                "id": f"score-{day:%Y%m%d}",
                "date": day,
                "title": target["title"],
                "description": "\n".join(description),
            })
        day += timedelta(days=1)
    return prompts


def common_notes(week: dict, targets: dict) -> list[str]:
    return [
        f"Weekly topic: {week['topic']}",
        f"TWIS: {'; '.join(week['twis'])}",
        f"SCORE focus: {'; '.join(week['score_topics'])}",
        f"Anki: {targets['anki_minutes']} minutes; make up to "
        f"{targets['anki_new_cards_cap']} cards from missed or guessed questions",
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

        target = score_target_for_day(plan, day, events)
        if not target or target["kind"] == "recovery":
            continue
        is_call = target["kind"] == "call"
        is_vacation = target["kind"] == "vacation"
        weekday = day.strftime("%A").lower()

        if weekday == case_day:
            notes = [
                target["instruction"],
                f"SCORE phase: {target['phase']['label']}",
                f"Modules: {'; '.join(week['twis'])}",
                f"Anki: {targets['anki_minutes']} minutes; make up to "
                f"{targets['anki_new_cards_cap']} cards from missed or guessed questions",
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
        notes.insert(0, f"SCORE phase: {target['phase']['label']}")
        if is_call:
            title = f"Optional study: {week['topic']}"
            duration = 15
            notes.insert(0, target["instruction"])
        elif is_vacation:
            title = f"Light study: {week['topic']}"
            duration = 20
            notes.insert(0, target["instruction"])
        elif weekday == deep_day:
            title = f"Deep study: {week['topic']}"
            duration = 120
            notes.insert(0, target["instruction"])
            notes.append(f"Preview this week's case: {week['case_review']}")
        else:
            title = f"Study: {week['topic']}"
            duration = 60
            notes.insert(0, target["instruction"])

        schedule[day].append({
            "id": f"study_{week['week_of']:%Y%m%d}_{weekday}",
            "title": title,
            "duration_minutes": duration,
            "notes": notes,
        })
    return schedule
