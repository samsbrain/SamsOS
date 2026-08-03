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

Required fields: `id`, `title`, `domain`, and `duration_minutes`. Weekly routines
use `recurrence: weekly` and lowercase weekday names in `days`. Monthly routines
use `recurrence: monthly`, `weekday`, and `week_of_month` (`first` or `last`).
Optional details include:

- `start_time`: local time in 24-hour `HH:MM` format, such as `19:00`
- `location`: human-readable place name
- `scheduling`: `fixed` when the commitment should be protected, or `flexible`
  when a future planner may move it

These fields describe the routine without yet creating or synchronizing an
external calendar event.

### Training plan

`training_plan` defines a flexible weekly target rather than fixed weekdays.
`weight_sessions_per_week` is the target count, and `duration_minutes` includes
the full gym commitment. Each item in `sessions` has a `name` and may include a
`notes` list. Those notes appear beneath the workout in the weekly plan and in
the subscribed calendar event's notes. The two `avoid_*` switches tell the
planner not to place weights on BJJ or yoga days.

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

### Study plan and progress

`Study/plan.yaml` defines the dated SCORE/TWIS curriculum, daily question and
Anki targets, and one integrated operation/case/anatomy/complication review per
week. The generator treats call study as optional, skips post-call study, and
uses a light vacation target. `Study/progress.yaml` stores manually updated
SCORE, TWIS, and case-review counters for the dashboard.

SCORE work has two distinct phases. The first phase completes the full question
bank. The second phase is a smaller focused review containing only missed,
guessed, and weak-topic questions. Each phase has separate totals, dates, and
normal/deep-study/call/vacation question targets; focused review is not treated
as a second complete pass. Its configured total is a ceiling, and review can
stop early when the flagged question queue is complete.

The Reminders feed includes one all-day SCORE prompt for every study-plan day.
Normal, deep-study, vacation, and call targets come from the active phase under
`daily_targets`; post-call days display a protected zero-question recovery
prompt. Each prompt includes the phase, scope, weekly module names, and the
configured Anki rule.

### Finance files

The monthly finance routine is configured in `Config/master.yaml`. Previous
`.xlsx`, `.xls`, `.csv`, and `.tsv` worksheets can be placed in `Finance/`; the
dashboard will list links to them automatically.

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
- `calendar_horizon_days`: number of days included in the public calendar feed

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

## Generated public files

`Generator/build_samos.py` validates the source data and generates the public
calendar artifacts in `public/`:

- `SamOS.ics`: rotations, call, vacation, training, and non-identifying cases
- `Reminders.ics`: deadline prompts generated from reminder profiles
- `dashboard.html`: read-only overview of today's plan, study progress, the
  current week, upcoming reminders, and finance worksheets

The public folder is a compiled output. YAML, case files, and knowledge notes
remain the source of truth.
