# SamOS Schema

## Purpose

The schema is SamOS's blueprint. It defines the shape of the information that the
generators will read. YAML stores the information; Python reads and checks it;
generators will later turn it into plans, calendars, and dashboards.

Version 0.1 deliberately defines only the stable core. Events, knowledge records,
and generated outputs will be added when a working feature needs them.

## Core files

- `Config/master.yaml` describes the person and what matters to them.
- `Config/rules.yaml` describes how SamOS should make decisions.

## Core objects

### Person

One mapping containing basic system-wide facts.

Required fields:

- `name`: text
- `timezone`: an IANA timezone such as `America/New_York`

### Role

A major identity or responsibility, such as surgeon or husband.

Required fields:

- `id`: stable, unique identifier written in `snake_case`
- `name`: human-readable name

### Domain

An area SamOS organizes, such as surgery, fitness, or finances.

Required fields:

- `id`: stable, unique identifier
- `name`: human-readable name

Optional fields:

- `role`: the `id` of the role this domain supports

### Goal

An outcome SamOS should help move toward.

Required fields: `id`, `title`, `domain`, `priority`, and `status`.
Priority is `low`, `medium`, or `high`. Status is `active`, `paused`, or
`complete`.

### Project

Finite work that advances a goal.

Required fields: `id`, `title`, `goal`, `status`, and `next_action`. The `goal`
must match an existing goal ID. `next_action` makes the project immediately
actionable instead of merely naming an ambition.

### Routine

An activity that repeats on named days.

Required fields: `id`, `title`, `domain`, `days`, and `duration_minutes`. Days
are lowercase weekday names. The first planner intentionally schedules by day,
with two optional details:

- `start_time`: local time in 24-hour `HH:MM` format, such as `19:00`
- `location`: human-readable place name
- `scheduling`: `fixed` when the commitment should be protected, or `flexible`
  when a future planner may move it

These fields describe the routine without yet creating or synchronizing an
external calendar event.

### Training plan

`training_plan` defines a flexible weekly target rather than fixed weekdays.
`weight_sessions_per_week` is the target count, `sessions` names each workout,
and `duration_minutes` includes the full gym commitment. The two `avoid_*`
switches tell the planner not to place weights on BJJ or yoga days.

### Monthly event

Files named `Monthly/YYYY-MM.yaml` hold dated schedule exceptions.

Required fields: `id`, `type`, `title`, `start`, and `end`. Type is `call`,
`vacation`, `rotation`, or `event`; dates use `YYYY-MM-DD`. A one-day event has
the same start and end date.

Call and vacation block training. A rotation provides context across its date
range but does not block training. Put a rotation in the monthly file containing
its start date, even when it continues into a later month:

```yaml
- id: trauma_rotation_2026_08
  type: rotation
  title: Trauma Surgery
  start: 2026-08-01
  end: 2026-08-31
```

### Reminder

`Reminders/reminders.yaml` is the single place for bills, presentations, date
planning, job applications, and miscellaneous deadlines. Each item has `id`,
`title`, `category`, `due`, and `status`.

`Config/reminder_profiles.yaml` defines how early and how often each category
prompts you. For example, a job application begins 180 days ahead, while a bill
begins 14 days ahead. Offsets become more frequent as the due date approaches.
Changing a profile changes every reminder in that category without editing each
item individually. The generator produces both `Dashboard/Reminders.md` and a
separate subscribable `Dashboard/Reminders.ics` feed. Each prompt is a
non-blocking all-day calendar entry with a stable ID, so rebuilding the feed
updates it without intentionally creating a new identity.

### Weekly case

`Cases/YYYY-MM-DD.yaml` stores the non-identifying case schedule for a week;
the filename and `week_of` use that week's Monday. A case contains `id`,
`procedure`, `date`, `start_time`, `duration_minutes`, and `tags`, with optional
`location` and `knowledge_topics`.

Never store patient names, initials, medical record numbers, birth dates, room
numbers, or other identifying information in SamOS.

### Knowledge topic

`Knowledge/index.yaml` connects a stable topic ID and tags to a durable Markdown
note. The case generator matches explicit `knowledge_topics` first and also
finds notes with overlapping tags. It produces `Dashboard/CaseBrief.md` and an
importable `Dashboard/Cases.ics` calendar.

### Preferences

Small defaults used by generators.

Required fields:

- `week_starts_on`: `monday` or `sunday`
- `planning_horizon_days`: whole number greater than zero

### Rule

A plain-language decision principle.

Required fields:

- `id`: stable, unique identifier
- `description`: what the rule means
- `enabled`: `true` or `false`

## How YAML becomes Python

This YAML:

```yaml
person:
  name: Sam
  timezone: America/New_York
```

loads as a Python dictionary:

```python
{
    "person": {
        "name": "Sam",
        "timezone": "America/New_York",
    }
}
```

A dictionary is a labeled container. Python retrieves the name with
`data["person"]["name"]`. Lists use dashes in YAML and become Python lists.

## Validation

Validation is a preflight checklist. `Generator/validate_config.py` checks that
required labels exist and that their values have the expected basic type. It
does not make planning decisions or generate output.
