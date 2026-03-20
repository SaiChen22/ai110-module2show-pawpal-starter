classDiagram
direction LR

class Owner {
+str name
+int available_minutes_per_day
+time preferred_start_time
+time preferred_end_time
+str notes
+int get_time_budget()
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
+str get_profile_summary()
+dict to_dict()
+Pet from_dict(dict data)
}

class Task {
+str task_id
+str name
+TaskCategory category
+int duration_minutes
+Priority priority
+bool is_recurring
+liststr recurrence_days
+tupletime,time preferred_time_window
+str notes
+bool is_schedulable_at(time t)
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
+listScheduledTask scheduled_tasks
+listTask unscheduled_tasks
+int total_minutes_scheduled
+liststr warnings
+void add_scheduled_task(ScheduledTask st)
+str get_summary()
+bool has_conflicts()
+DataFrame to_display_df()
}

class Scheduler {
+Owner owner
+Pet pet
+listTask tasks
+DailyPlan generate_plan(date target_date)
-listTask _sort_tasks_by_priority(listTask tasks)
-time _find_next_available_slot(DailyPlan plan, Task task)
-bool _check_time_window_preference(Task task, time proposed_time)
-str _explain_placement(Task task, time proposed_time)
-liststr _handle_overflow(listTask unfit_tasks)
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

Owner "1" --> "1" Pet : owns
Owner "1" --> "0..*" Task : tracks
Scheduler --> Owner : uses
Scheduler --> Pet : uses
Scheduler --> Task : uses
Scheduler --> DailyPlan : produces
DailyPlan *-- ScheduledTask : contains
DailyPlan --> Task : unscheduled
ScheduledTask --> Task : wraps
Task --> Priority
Task --> TaskCategory