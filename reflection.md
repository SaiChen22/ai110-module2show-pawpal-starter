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

I used VS Code Copilot in three main ways: architecture brainstorming, targeted implementation help, and fast test expansion. The most effective features were codebase-aware chat prompts (using #codebase context), inline code completion for repetitive dataclass and test patterns, and iterative refactor suggestions for keeping method responsibilities small.

The most helpful prompts were specific and constraint-driven. For example, asking Copilot to "add tests for sorting correctness, daily recurrence rollover, and duplicate-time conflict warnings" produced better results than broad prompts like "improve tests." Prompts that named expected behavior and failure conditions were consistently the highest quality.

**b. Judgment and verification**

One suggestion I did not accept as-is was a more aggressive "auto-relax exact preferred times" scheduling behavior (moving strict-time tasks to nearby slots automatically). I rejected that because it would blur user intent and make medication/feeding routines less predictable. Instead, I kept strict preferred-time handling and surfaced conflict warnings clearly.

I evaluated AI suggestions with two checks: design clarity and test evidence. If a suggestion made responsibilities ambiguous or mixed concerns across classes, I rewrote it. If behavior changed, I required passing tests (especially for sorting, recurrence, and conflicts) before accepting the change.

**c. Separate chat sessions and organization**

Using separate Copilot chat sessions by phase was very helpful. I used one session for UML/design reasoning, another for core scheduler implementation, another for test coverage, and another for documentation polish. This kept context focused, reduced prompt drift, and made it easier to compare decisions without mixing unrelated threads.

**d. Lead architect takeaway**

My key learning was that strong AI tools do not replace architecture ownership. As the "lead architect," my job was to define constraints, choose tradeoffs, and protect system boundaries while using AI for speed. The best outcomes came when I treated Copilot as a high-velocity collaborator, but kept final responsibility for coherence, correctness, and maintainability.

---

## 4. Testing and Verification

**a. What you tested**

I tested the behaviors that are most likely to break user trust in a scheduler:

- Task completion state transitions (`mark_complete` / `mark_completed`).
- Sorting correctness (priority ordering and chronological ordering by preferred time).
- Filtering behavior (by pet, completion status, task name, and pet name).
- Recurrence logic (daily tasks due every day, weekly day-based recurrence, and rollover creation after completion).
- Conflict logic (task overlap detection, boundary non-overlap cases, and warning generation for duplicate preferred times).
- Convenience retrieval methods (pending tasks, recurring tasks, category and high-priority views).

These tests were important because scheduling bugs are often subtle and cumulative. A small logic mistake in sorting, due-date evaluation, or overlap detection can produce plans that look plausible but are behaviorally wrong. The test suite gave fast feedback while refactoring and made it safe to evolve the scheduler without regressions.

**b. Confidence**

I am highly confident that the current scheduler works correctly for the implemented feature scope. The suite passes consistently (`29 passed`) and covers the critical execution path from task retrieval to placement, warning generation, and recurrence rollover.

If I had more time, I would add edge-case tests for:

- Deterministic ordering when multiple tasks tie on priority, preferred time, and duration.
- Weekly recurrence with invalid weekday names or empty recurrence lists.
- Date-boundary recurrence cases (end-of-month, year rollover, leap-year transitions).
- Duplicate completion protection (ensuring repeated complete actions do not create unintended duplicate future tasks).
- Stress/performance scenarios with many tasks across multiple pets.

---

## 5. Reflection

**a. What went well**

The part I am most satisfied with is the separation of concerns in the final design. Domain entities (`Owner`, `Pet`, `Task`) remain focused on state and local behavior, while `Scheduler` handles orchestration. That separation made both debugging and UI integration much cleaner. I am also satisfied with how recurrence and conflict warnings were implemented in a way that is practical for real user workflows.

**b. What you would improve**

With another iteration, I would redesign the scheduler around a pluggable strategy interface so different planning policies (strict routine, balanced load, urgency-first) could be swapped without changing core models. I would also add richer constraint configuration in the UI (for example, per-task flexibility level), and introduce persistent storage so plans and completion history survive app restarts.

**c. Key takeaway**

One important takeaway is that AI amplifies both good and bad direction. When I provided clear requirements, constraints, and acceptance tests, development accelerated without losing design quality. When prompts were vague, suggestions were less aligned. Being explicit about architecture intent was the biggest factor in getting reliable results.
