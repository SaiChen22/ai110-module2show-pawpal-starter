classDiagram
direction LR

class PawPalException {
}

class ValidationError {
}

class TimeConstraintError {
}

class DurationError {
}

class Owner {
+str name
+int available_minutes_per_day
+time preferred_start_time
+time preferred_end_time
+str notes
+str owner_id
+list~Pet~ pets
+int get_time_budget()
+void add_pet(Pet pet)
+bool remove_pet(str pet_id)
+list~Task~ get_all_tasks()
+dict to_dict()
+Owner from_dict(dict data)
}

class Pet {
+str name
+str species
+str breed
+float age_years
+float weight_kg
+str health_notes
+str pet_id
+str owner_id
+list~Task~ tasks
+str get_profile_summary()
+dict to_dict()
+void add_task(Task task)
+bool remove_task(str task_id)
+list~Task~ get_tasks_due_on(date target_date)
+Pet from_dict(dict data)
}

class Task {
+str task_id
+str owner_id
+str pet_id
+str name
+TaskCategory category
+int duration_minutes
+Priority priority
+bool is_recurring
+list~str~ recurrence_days
+tuple~time,time~ preferred_time_window
+time preferred_time
+str frequency
+bool is_completed
+date completed_on
+date scheduled_for
+str notes
+bool is_schedulable_at(time t)
+void mark_completed(date completed_date)
+void mark_complete(date completed_date)
+date get_next_occurrence_date(date from_date)
+Task create_next_occurrence(date completed_date)
+void mark_pending()
+bool is_due_on(date target_date)
+dict to_dict()
+Task from_dict(dict data)
}

class ScheduledTask {
+Task task
+time start_time
+time end_time
+str reasoning
+bool overlaps_with(ScheduledTask other)
+int duration()
}

class DailyPlan {
+date date
+list~ScheduledTask~ scheduled_tasks
+list~Task~ unscheduled_tasks
+int total_minutes_scheduled
+list~str~ warnings
+str owner_id
+str pet_id
+void add_scheduled_task(ScheduledTask st)
+str get_summary()
+bool has_conflicts()
+list~tuple~ find_conflicts_sorted()
+DataFrame to_display_df()
}

class Scheduler {
+Owner owner
+Pet pet
+list~Task~ tasks
+DailyPlan generate_plan(date target_date)
+Task mark_task_completed(str task_id, date completed_date)
+list~Task~ get_tasks_for_pet(str pet_id)
+list~Task~ get_pending_tasks(date target_date)
+list~Task~ get_recurring_tasks()
+list~Task~ get_tasks_by_category(TaskCategory category)
+list~Task~ get_high_priority_tasks(date target_date)
+list~dict~ sort_by_time(list~Task~ tasks)
+list~Task~ filter_tasks(bool is_completed, str name, str pet_name, list~Task~ tasks)
-list~Task~ _retrieve_owner_pet_tasks(date target_date)
-list~Task~ _sort_tasks_by_priority(list~Task~ tasks)
-time _find_next_available_slot(DailyPlan plan, Task task)
-tuple~time,time~ _resolve_effective_window(Task task)
-bool _can_fit_in_gap(time start, time gap_end, Task task, time window_end)
-bool _is_candidate_non_overlapping(DailyPlan plan, Task task, time candidate)
-bool _check_time_window_preference(Task task, time proposed_time)
-str _explain_placement(Task task, time proposed_time)
-list~str~ _handle_overflow(list~Task~ unfit_tasks)
-list~str~ _detect_lightweight_conflicts(list~Task~ tasks, DailyPlan plan)
}

class Priority {
<<enumeration>>
HIGH
MEDIUM
LOW
}

class TaskCategory {
<<enumeration>>
WALK
FEED
MEDICATION
GROOMING
ENRICHMENT
VET
OTHER
}

PawPalException <|-- ValidationError
ValidationError <|-- TimeConstraintError
ValidationError <|-- DurationError

Owner "1" *-- "0..*" Pet : owns
Pet "1" *-- "0..*" Task : has
Scheduler --> Owner : uses
Scheduler --> Pet : optional scope
Scheduler --> Task : uses
Scheduler --> DailyPlan : produces
DailyPlan *-- ScheduledTask : contains
DailyPlan --> Task : unscheduled
ScheduledTask --> Task : wraps
Task --> Priority
Task --> TaskCategory