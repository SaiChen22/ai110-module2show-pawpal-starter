# PawPal+ Project Reflection

## 1. System Design

**a. Initial design**

My initial UML design includes six core classes plus two enumerations:

**Owner** represents a pet owner and tracks their availability constraints: daily time budget (in minutes), preferred start/end times, and any relevant notes. Its responsibility is to store owner preferences and provide access to time budget via `get_time_budget()`. It also handles serialization through `to_dict()` and `from_dict()` for persistence.

**Pet** represents a pet and maintains its profile: name, species, breed, age, weight, and health notes. Its primary responsibility is to provide a formatted profile summary via `get_profile_summary()` and handle serialization.

**Task** represents a schedulable activity for the pet. It stores the task name, category (walk, feed, medication, etc.), duration, priority level, recurrence information, optional time window preferences, and notes. Its responsibilities include determining if it can be scheduled at a given time via `is_schedulable_at()` and serialization.

**ScheduledTask** wraps a Task with concrete scheduling information: the start time and reasoning for that placement. It automatically calculates the end time, can check for overlaps with other scheduled tasks, and report its duration.

**DailyPlan** represents a single day's schedule. It contains lists of scheduled tasks, unscheduled tasks, warning messages, and total time used. Its responsibilities are adding tasks while maintaining sort order, checking for conflicts, retrieving a summary, and generating a display DataFrame for easy visualization.

**Scheduler** is the orchestrator that coordinates Owner, Pet, and Task data to produce a DailyPlan. It declares the main entry point `generate_plan()` plus helper methods for sorting by priority, finding available slots, validating time preferences, explaining placements, and handling overflow tasks.

**Priority** and **TaskCategory** are enumerations for consistent task classification across the system.

**b. Design changes**

Yes, the design changed during implementation. The biggest change was adding a formal validation layer with custom exceptions (`ValidationError`, `TimeConstraintError`, and `DurationError`) plus helper validators for positive values and valid time ranges. In the initial UML, `from_dict()` methods mostly focused on type conversion, but in practice I realized that accepting invalid values (like negative durations or end times before start times) would silently create bad state and make scheduling bugs harder to trace. Moving validation to deserialization made the model fail fast and kept invalid data out of the system.

I also added explicit relationship fields (`owner_id` and `pet_id`) to `Task`, and added matching context fields on `DailyPlan`. The initial design assumed a single owner-pet context managed by `Scheduler`, but this was too implicit. Adding IDs made relationships explicit, made serialization more robust, and prepared the design for multi-pet or multi-owner scenarios without rewriting core models.

Another change was expanding conflict analysis in `DailyPlan`. The original conflict check used a simple pairwise comparison. I kept that behavior, but added `find_conflicts_sorted()` using a sweep-line style approach to make conflict detection more scalable and to return the exact conflicting pairs. This improved observability and performance while preserving the original API.

---

## 2. Scheduling Logic and Tradeoffs

**a. Constraints and priorities**

The scheduler considers four main constraints: (1) owner time budget per day, (2) owner preferred start/end window, (3) task-level time preferences (exact preferred_time or preferred_time_window), and (4) task priority (HIGH, MEDIUM, LOW). It also filters by due date/recurrence and completion status so only relevant tasks are considered.

I prioritized constraints in this order: validity first (time windows and non-overlap), then feasibility (daily budget), then urgency (priority), then user preference fit (preferred times). That order reflects the scenario: a usable plan must be conflict-free and realistic before it can be optimal.

**b. Tradeoffs**

One tradeoff is that tasks with an exact preferred_time are treated as strict requests. If that exact slot is blocked, the scheduler does not automatically relax to nearby times for that task. This keeps placement logic simple and predictable, and supports clear conflict warnings (for example, two tasks both requested at 08:00).

This is reasonable for the current pet-care scenario because predictability is often more important than aggressive optimization. Owners usually care about consistent routines (medication, feeding windows), so failing fast with a warning and suggesting manual adjustment is safer than silently moving sensitive tasks.

---

## 3. AI Collaboration

**a. How you used AI**

- How did you use AI tools during this project (for example: design brainstorming, debugging, refactoring)?
- What kinds of prompts or questions were most helpful?

**b. Judgment and verification**

- Describe one moment where you did not accept an AI suggestion as-is.
- How did you evaluate or verify what the AI suggested?

---

## 4. Testing and Verification

**a. What you tested**

- What behaviors did you test?
- Why were these tests important?

**b. Confidence**

- How confident are you that your scheduler works correctly?
- What edge cases would you test next if you had more time?

---

## 5. Reflection

**a. What went well**

- What part of this project are you most satisfied with?

**b. What you would improve**

- If you had another iteration, what would you improve or redesign?

**c. Key takeaway**

- What is one important thing you learned about designing systems or working with AI on this project?
