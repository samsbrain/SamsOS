"""Check the small SamOS v0.1 configuration before generators use it."""

from datetime import date, time
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "Config"
DAYS = {"monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"}
PRIORITIES = {"low", "medium", "high"}
STATUSES = {"active", "paused", "complete"}


def load_yaml(filename: str) -> dict:
    """Load one YAML file and require a dictionary at its top level."""
    path = CONFIG / filename
    if not path.exists():
        path = ROOT / filename
    with path.open(encoding="utf-8") as file:
        data = yaml.safe_load(file)
    if not isinstance(data, dict):
        raise ValueError(f"{filename}: top level must be a mapping of labeled fields")
    return data


def require_fields(data: dict, fields: tuple[str, ...], location: str) -> None:
    """Raise a readable error when a required field is absent."""
    missing = [field for field in fields if field not in data]
    if missing:
        raise ValueError(f"{location}: missing {', '.join(missing)}")


def validate_master(data: dict) -> None:
    require_fields(
        data,
        (
            "person", "roles", "domains", "goals", "projects", "routines",
            "training_plan", "preferences",
        ),
        "master.yaml",
    )
    require_fields(data["person"], ("name", "timezone"), "master.yaml > person")

    for list_name in ("roles", "domains", "goals", "projects", "routines"):
        if not isinstance(data[list_name], list):
            raise ValueError(f"master.yaml > {list_name}: must be a list")

    role_ids = set()
    for index, role in enumerate(data["roles"]):
        require_fields(role, ("id", "name"), f"master.yaml > roles > item {index + 1}")
        if role["id"] in role_ids:
            raise ValueError(f"master.yaml > roles: duplicate id '{role['id']}'")
        role_ids.add(role["id"])

    domain_ids = set()
    for index, domain in enumerate(data["domains"]):
        require_fields(domain, ("id", "name"), f"master.yaml > domains > item {index + 1}")
        if domain["id"] in domain_ids:
            raise ValueError(f"master.yaml > domains: duplicate id '{domain['id']}'")
        domain_ids.add(domain["id"])
        if "role" in domain and domain["role"] not in role_ids:
            raise ValueError(
                f"master.yaml > domains > {domain['id']}: unknown role '{domain['role']}'"
            )

    goal_ids = set()
    for index, goal in enumerate(data["goals"]):
        location = f"master.yaml > goals > item {index + 1}"
        require_fields(goal, ("id", "title", "domain", "priority", "status"), location)
        if goal["id"] in goal_ids:
            raise ValueError(f"master.yaml > goals: duplicate id '{goal['id']}'")
        if goal["domain"] not in domain_ids:
            raise ValueError(f"{location}: unknown domain '{goal['domain']}'")
        if goal["priority"] not in PRIORITIES:
            raise ValueError(f"{location}: priority must be low, medium, or high")
        if goal["status"] not in STATUSES:
            raise ValueError(f"{location}: status must be active, paused, or complete")
        goal_ids.add(goal["id"])

    project_ids = set()
    for index, project in enumerate(data["projects"]):
        location = f"master.yaml > projects > item {index + 1}"
        require_fields(project, ("id", "title", "goal", "status", "next_action"), location)
        if project["id"] in project_ids:
            raise ValueError(f"master.yaml > projects: duplicate id '{project['id']}'")
        if project["goal"] not in goal_ids:
            raise ValueError(f"{location}: unknown goal '{project['goal']}'")
        if project["status"] not in STATUSES:
            raise ValueError(f"{location}: status must be active, paused, or complete")
        project_ids.add(project["id"])

    routine_ids = set()
    for index, routine in enumerate(data["routines"]):
        location = f"master.yaml > routines > item {index + 1}"
        require_fields(routine, ("id", "title", "domain", "days", "duration_minutes"), location)
        if routine["id"] in routine_ids:
            raise ValueError(f"master.yaml > routines: duplicate id '{routine['id']}'")
        if routine["domain"] not in domain_ids:
            raise ValueError(f"{location}: unknown domain '{routine['domain']}'")
        if not isinstance(routine["days"], list) or not routine["days"]:
            raise ValueError(f"{location}: days must be a non-empty list")
        unknown_days = set(routine["days"]) - DAYS
        if unknown_days:
            raise ValueError(f"{location}: unknown day '{sorted(unknown_days)[0]}'")
        minutes = routine["duration_minutes"]
        if not isinstance(minutes, int) or isinstance(minutes, bool) or minutes < 1:
            raise ValueError(f"{location}: duration_minutes must be a positive integer")
        if "start_time" in routine:
            try:
                time.fromisoformat(routine["start_time"])
            except (TypeError, ValueError):
                raise ValueError(f"{location}: start_time must use 24-hour HH:MM format") from None
        if "location" in routine and not isinstance(routine["location"], str):
            raise ValueError(f"{location}: location must be text")
        if "scheduling" in routine and routine["scheduling"] not in {"fixed", "preferred", "flexible"}:
            raise ValueError(f"{location}: scheduling must be fixed, preferred, or flexible")
        routine_ids.add(routine["id"])

    training = data["training_plan"]
    require_fields(
        training,
        ("weight_sessions_per_week", "duration_minutes", "avoid_bjj_days", "avoid_yoga_days", "sessions"),
        "master.yaml > training_plan",
    )
    target = training["weight_sessions_per_week"]
    if not isinstance(target, int) or isinstance(target, bool) or target < 0 or target > 7:
        raise ValueError("master.yaml > training_plan > weight_sessions_per_week: use 0 through 7")
    if not isinstance(training["sessions"], list) or len(training["sessions"]) != target:
        raise ValueError("master.yaml > training_plan > sessions: list one name per weekly session")
    for field in ("avoid_bjj_days", "avoid_yoga_days"):
        if not isinstance(training[field], bool):
            raise ValueError(f"master.yaml > training_plan > {field}: use true or false")

    preferences = data["preferences"]
    require_fields(
        preferences,
        ("week_starts_on", "planning_horizon_days", "calendar_horizon_days"),
        "master.yaml > preferences",
    )
    if preferences["week_starts_on"] not in {"monday", "sunday"}:
        raise ValueError("master.yaml > preferences > week_starts_on: use monday or sunday")
    days = preferences["planning_horizon_days"]
    if not isinstance(days, int) or isinstance(days, bool) or days < 1:
        raise ValueError("master.yaml > preferences > planning_horizon_days: use a positive integer")
    horizon = preferences["calendar_horizon_days"]
    if not isinstance(horizon, int) or isinstance(horizon, bool) or horizon < 1:
        raise ValueError("master.yaml > preferences > calendar_horizon_days: use a positive integer")


def validate_rules(data: dict) -> None:
    require_fields(data, ("rules",), "rules.yaml")
    if not isinstance(data["rules"], list):
        raise ValueError("rules.yaml > rules: must be a list")
    rule_ids = set()
    for index, rule in enumerate(data["rules"]):
        require_fields(rule, ("id", "description", "enabled"), f"rules.yaml > item {index + 1}")
        if rule["id"] in rule_ids:
            raise ValueError(f"rules.yaml: duplicate id '{rule['id']}'")
        if not isinstance(rule["enabled"], bool):
            raise ValueError(f"rules.yaml > {rule['id']} > enabled: use true or false")
        rule_ids.add(rule["id"])


def validate_month(data: dict, filename: str) -> None:
    require_fields(data, ("month", "events"), filename)
    if not isinstance(data["events"], list):
        raise ValueError(f"{filename} > events: must be a list")
    event_ids = set()
    for index, event in enumerate(data["events"]):
        location = f"{filename} > events > item {index + 1}"
        require_fields(event, ("id", "type", "title", "start", "end"), location)
        if event["id"] in event_ids:
            raise ValueError(f"{filename}: duplicate id '{event['id']}'")
        if event["type"] not in {"call", "vacation", "rotation", "event"}:
            raise ValueError(f"{location}: type must be call, vacation, rotation, or event")
        if not isinstance(event["start"], date) or not isinstance(event["end"], date):
            raise ValueError(f"{location}: start and end must be YYYY-MM-DD dates")
        if event["end"] < event["start"]:
            raise ValueError(f"{location}: end cannot be before start")
        event_ids.add(event["id"])


def validate_reminder_profiles(data: dict) -> None:
    require_fields(data, ("profiles",), "reminder_profiles.yaml")
    if not isinstance(data["profiles"], dict) or not data["profiles"]:
        raise ValueError("reminder_profiles.yaml > profiles: must be a non-empty mapping")
    for name, profile in data["profiles"].items():
        require_fields(profile, ("reminder_days_before",), f"reminder_profiles.yaml > {name}")
        offsets = profile["reminder_days_before"]
        if not isinstance(offsets, list) or not offsets:
            raise ValueError(f"reminder_profiles.yaml > {name}: use a non-empty list")
        if any(not isinstance(value, int) or isinstance(value, bool) or value < 0 for value in offsets):
            raise ValueError(f"reminder_profiles.yaml > {name}: offsets must be whole numbers of days")
        if len(offsets) != len(set(offsets)):
            raise ValueError(f"reminder_profiles.yaml > {name}: offsets must be unique")


def validate_reminders(data: dict, profile_names: set[str]) -> None:
    require_fields(data, ("reminders",), "reminders.yaml")
    if not isinstance(data["reminders"], list):
        raise ValueError("reminders.yaml > reminders: must be a list")
    ids = set()
    for index, item in enumerate(data["reminders"]):
        location = f"reminders.yaml > item {index + 1}"
        require_fields(item, ("id", "title", "category", "due", "status"), location)
        if item["id"] in ids:
            raise ValueError(f"reminders.yaml: duplicate id '{item['id']}'")
        if item["category"] not in profile_names:
            raise ValueError(f"{location}: unknown category '{item['category']}'")
        if not isinstance(item["due"], date):
            raise ValueError(f"{location}: due must be a YYYY-MM-DD date")
        if item["status"] not in {"active", "complete"}:
            raise ValueError(f"{location}: status must be active or complete")
        ids.add(item["id"])


def validate_knowledge(data: dict) -> None:
    require_fields(data, ("topics",), "Knowledge/index.yaml")
    if not isinstance(data["topics"], list):
        raise ValueError("Knowledge/index.yaml > topics: must be a list")
    ids = set()
    for index, topic in enumerate(data["topics"]):
        location = f"Knowledge/index.yaml > item {index + 1}"
        require_fields(topic, ("id", "title", "tags", "note"), location)
        if topic["id"] in ids:
            raise ValueError(f"Knowledge/index.yaml: duplicate id '{topic['id']}'")
        if not isinstance(topic["tags"], list):
            raise ValueError(f"{location}: tags must be a list")
        ids.add(topic["id"])


def validate_cases(data: dict, filename: str) -> None:
    require_fields(data, ("week_of", "cases"), f"Cases/{filename}.yaml")
    if not isinstance(data["week_of"], date) or data["week_of"].weekday() != 0:
        raise ValueError(f"Cases/{filename}.yaml > week_of: must be a Monday date")
    if not isinstance(data["cases"], list):
        raise ValueError(f"Cases/{filename}.yaml > cases: must be a list")
    ids = set()
    for index, case in enumerate(data["cases"]):
        location = f"Cases/{filename}.yaml > item {index + 1}"
        require_fields(case, ("id", "procedure", "date", "start_time", "duration_minutes", "tags"), location)
        if case["id"] in ids:
            raise ValueError(f"Cases/{filename}.yaml: duplicate id '{case['id']}'")
        if not isinstance(case["date"], date):
            raise ValueError(f"{location}: date must use YYYY-MM-DD")
        try:
            time.fromisoformat(case["start_time"])
        except (TypeError, ValueError):
            raise ValueError(f"{location}: start_time must use quoted HH:MM format") from None
        if not isinstance(case["duration_minutes"], int) or case["duration_minutes"] < 1:
            raise ValueError(f"{location}: duration_minutes must be positive")
        if not isinstance(case["tags"], list):
            raise ValueError(f"{location}: tags must be a list")
        ids.add(case["id"])


def main() -> None:
    validate_master(load_yaml("master.yaml"))
    validate_rules(load_yaml("rules.yaml"))
    profiles = load_yaml("reminder_profiles.yaml")
    validate_reminder_profiles(profiles)
    validate_reminders(load_yaml("Reminders/reminders.yaml"), set(profiles["profiles"]))
    validate_knowledge(load_yaml("Knowledge/index.yaml"))
    for path in sorted((ROOT / "Cases").glob("????-??-??.yaml")):
        validate_cases(load_yaml(str(path.relative_to(ROOT))), path.stem)
    for path in sorted((ROOT / "Monthly").glob("????-??.yaml")):
        validate_month(load_yaml(str(path.relative_to(ROOT))), path.name)
    print("SamOS configuration is valid.")


if __name__ == "__main__":
    main()
