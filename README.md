# SamOS

The organizer for all things residency, life and improving myself.

## Mission

Reduce decision fatigue by organizing every aspect of life, work, and training into one place.

## Areas

- 📅 Master Calendar
- 📚🧠 Knowledge Repository
  > oral board preparation
  > case walkthrough
  > clinical pearls
  > high yield topic reviews
- 💪 Training (BJJ/weights/cardio)
- 📊 Dashboard (eventually)

Current Version:
v0.1

## Current workflow

SamOS now has one build that validates the source data and refreshes the weekly
plan, reminders, calendar feeds, study schedule, and read-only dashboard:

```text
YAML source files -> validation -> plans, calendars, reminders, and dashboard
```

From the repository folder, install the YAML reader once:

```powershell
python -m pip install -r requirements.txt
```

Then build every generated output:

```powershell
python Generator/build_samos.py
```

To generate a different week, pass any date inside that week:

```powershell
python Generator/planner.py --week 2026-08-03
```

Edit `Config/master.yaml`, run the planner again, and open
`Dashboard/WeeklyPlan.md` to see the updated result.

The build also creates `Dashboard/Home.md` and the read-only web dashboard at
`public/dashboard.html`. Study assignments come from `Study/plan.yaml`, and
progress counters live in `Study/progress.yaml`.

Add deadlines to `Reminders/reminders.yaml`, then run the reminder generator to
update `Dashboard/Reminders.md` and the subscribable `Dashboard/Reminders.ics`.

Each Sunday, add the next week's non-identifying cases to a dated file under
`Cases/`, then run the case generator. It builds a cross-referenced case brief
and an importable calendar file. Never put protected patient information in the
repository.

## Build and calendar subscriptions

Build every validated output with one command:

```powershell
python Generator/build_samos.py
```

GitHub Actions runs that build on every push to `main` and once daily. GitHub
Pages publishes only the safe files under `public/`; it does not publish the
knowledge repository through the Pages workflow.

Subscribe to these addresses after GitHub Pages is enabled:

- Apple Calendar: `https://samsbrain.github.io/SamsOS/calendar.ics`
- Standards feed: `https://samsbrain.github.io/SamsOS/SamOS.ics`
- `https://samsbrain.github.io/SamsOS/Reminders.ics`
- Dashboard: `https://samsbrain.github.io/SamsOS/dashboard.html`

The first two addresses contain the same safe schedule information in different
timestamp formats. The final feed contains non-blocking, all-day deadline
prompts. Never add PHI to calendar or case files.
