# SamOS Architecture
> Architecture evolves. Principles are stable.
## Table of Contents
1. Purpose
2. Architectural Goals
3. Source of Truth
4. System Architecture
5. Design Philosophy
6. System Components
7. Data Flow
8. Feedback Loops
9. Inputs & Outputs
10. Object Hierarchy
11. Design Principles
12. Future Expansion
    
## Purpose

SamOS is a personal operating system designed to reduce cognitive load by transforming structured information about life into actionable daily plans.

It serves as the central coordination system for scheduling, knowledge management, planning, reminders, reflection, and long-term growth.

Rather than functioning as a calendar, SamOS acts as a planning platform that generates multiple outputs from a single source of truth.
## Architectural Goals

SamOS is designed to:

- Reduce cognitive load.
- Preserve knowledge gained through experience.
- Generate actionable daily plans.
- Maintain a single source of truth.
- Continuously improve through feedback.
- Scale throughout every stage of life.
---
## Source of Truth

SamOS stores structured information in GitHub using human-readable YAML files.

These files are the authoritative source of all planning, scheduling, knowledge, and reminders.

Outputs such as calendars, dashboards, and reminders are generated from this source and should never become independent sources of information.

---

## System Architecture
                Configuration
        ┌────────────┬────────────┐
        │            │            │
   master.yaml  monthly.yaml  knowledge.yaml
        │            │            │
        └────────────┴────────────┘
                     │
                Rules Engine
                     │
               Planning Engine
                     │
               Context Engine
                     │
         ┌───────────┼────────────┐
         │           │            │
     Calendar    Dashboard   Reminders
                     │
              Daily Reflection
                     │
             Knowledge Engine
                     │
             knowledge.yaml

---

## Design Philosophy

Everything is an object.

Objects contain information.

Templates define presentation.

Rules determine behavior.

Generators create outputs.

Knowledge compounds.

Everything has one source of truth.

Every piece of information should exist only in one place.

SamOS is designed around data, not interfaces. Interfaces may change; the data model should remain stable.

---

## System Components
| Component | Responsibility |
|-----------|----------------|
| Identity Engine | Defines who the user is and long-term defaults |
| Rules Engine | Applies behavioral logic |
| Planning Engine | Generates the optimal schedule |
| Knowledge Engine | Stores and retrieves accumulated knowledge |
| Output Generators | Build calendars, reminders, dashboards |

---

## Data Flow
Configuration Files
        ↓
Domain Objects
        ↓
Planning Engine
        ↓
Output Generators
        ↓
Execution
        ↓
Reflection
        ↓
Knowledge Base
        ↓
Future Planning
                     
---

## Feedback Loops
1. Learning Loop
   Study
   ↓
   Operate
   ↓
   Reflect
   ↓
   Knowledge
   ↓
   Better Study
2. Fitness Loop
   Workout
   ↓
   Recovery
   ↓
   Performance
   ↓
   Adjust Training
3.  Life Loop
    Plan
    ↓
    Execute
    ↓
    Weekly Review
    ↓
    Adjust Plan
---
##Inputs & Outputs
| Input | Description |
|--------|-------------|
| master.yaml | Identity and long-term defaults |
| rules.yaml | Decision logic |
| monthly.yaml | Monthly schedule and events |
| knowledge.yaml | Accumulated knowledge |
| Templates | Presentation rules |

| Output | Purpose |
|---------|---------|
| Calendar | Daily execution |
| Dashboard | Situational awareness |
| Reminders | Action prompts |
| Weekly Brief | Planning summary |
| Reflection Prompts | Continuous learning |
---

## Object Hierarchy

SamOS
│
├── Core
│   ├── Person
│   ├── Role
│   ├── Domain
│   └── Rule
│
├── Planning
│   ├── Event
│   ├── Case
│   ├── Call
│   ├── Rotation
│   └── Vacation
│
├── Growth
│   ├── StudyBlock
│   ├── Workout
│   ├── Reflection
│   ├── Knowledge
│   └── Goal
│
└── Presentation
    └── Template

---

## Design Principles
- Every object has a single source of truth.
- Behavior belongs in rules, not data.
- Presentation belongs in templates.
- Objects are immutable inputs; generators produce outputs.
- Knowledge should accumulate rather than be overwritten.
- New features should reuse existing objects whenever possible.

---

## Future Expansion

The architecture is designed to support future integrations without changing the underlying data model.

Potential future outputs include:

- Mobile widgets
- AI-assisted planning
- Health data integration
- Financial dashboards
- Travel planning
- Team collaboration

## Edit History
Version: 0.1
Status: Draft
Last Updated: 2026-07-30
