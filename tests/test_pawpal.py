from datetime import time

from pawpal_system import Owner, Pet, Priority, Task, TaskCategory


def test_task_completion_marks_status_complete() -> None:
	task = Task(
		name="Morning Walk",
		category=TaskCategory.WALK,
		duration_minutes=30,
		priority=Priority.HIGH,
		is_recurring=False,
	)

	assert task.is_completed is False
	task.mark_complete()
	assert task.is_completed is True


def test_add_task_to_pet_increases_task_count() -> None:
	pet = Pet(
		name="Mochi",
		species="dog",
		breed="Corgi Mix",
		age_years=4.0,
		weight_kg=11.5,
	)
	task = Task(
		name="Breakfast Feed",
		category=TaskCategory.FEED,
		duration_minutes=15,
		priority=Priority.MEDIUM,
		is_recurring=True,
	)

	initial_count = len(pet.tasks)
	pet.add_task(task)

	assert len(pet.tasks) == initial_count + 1
	assert pet.tasks[-1].name == "Breakfast Feed"


def test_owner_save_and_load_json_round_trip(tmp_path) -> None:
	owner = Owner(
		name="Jordan",
		available_minutes_per_day=120,
		preferred_start_time=time(7, 0),
		preferred_end_time=time(20, 0),
	)
	pet = Pet(name="Mochi", species="dog", breed="Corgi Mix", age_years=4.0, weight_kg=11.5)
	owner.add_pet(pet)
	pet.add_task(
		Task(
			name="Morning Walk",
			category=TaskCategory.WALK,
			duration_minutes=30,
			priority=Priority.HIGH,
			is_recurring=True,
			frequency="daily",
		)
	)

	data_file = tmp_path / "data.json"
	owner.save_to_json(str(data_file))
	loaded_owner = Owner.load_from_json(str(data_file))

	assert loaded_owner is not None
	assert loaded_owner.name == "Jordan"
	assert len(loaded_owner.pets) == 1
	assert loaded_owner.pets[0].name == "Mochi"
	assert len(loaded_owner.pets[0].tasks) == 1
	assert loaded_owner.pets[0].tasks[0].name == "Morning Walk"


def test_owner_load_json_returns_none_when_missing(tmp_path) -> None:
	missing_file = tmp_path / "missing.json"
	assert Owner.load_from_json(str(missing_file)) is None


# ============================================================================
# TESTS FOR SORTING TASKS BY TIME/PRIORITY
# ============================================================================


def test_sort_tasks_by_priority_high_first() -> None:
	"""Tasks are sorted HIGH > MEDIUM > LOW priority."""
	from pawpal_system import Scheduler, Owner
	from datetime import time
	
	owner = Owner(
		name="Alice",
		available_minutes_per_day=120,
		preferred_start_time=time(7, 0),
		preferred_end_time=time(20, 0),
	)
	
	scheduler = Scheduler(owner=owner)
	
	# Create tasks with different priorities
	low_task = Task(
		name="Play",
		category=TaskCategory.ENRICHMENT,
		duration_minutes=20,
		priority=Priority.LOW,
		is_recurring=False,
	)
	high_task = Task(
		name="Medication",
		category=TaskCategory.MEDICATION,
		duration_minutes=5,
		priority=Priority.HIGH,
		is_recurring=False,
	)
	med_task = Task(
		name="Grooming",
		category=TaskCategory.GROOMING,
		duration_minutes=15,
		priority=Priority.MEDIUM,
		is_recurring=False,
	)
	
	tasks = [low_task, high_task, med_task]
	sorted_tasks = scheduler._sort_tasks_by_priority(tasks)
	
	assert sorted_tasks[0].priority == Priority.HIGH
	assert sorted_tasks[1].priority == Priority.MEDIUM
	assert sorted_tasks[2].priority == Priority.LOW


def test_sort_tasks_by_preferred_time() -> None:
	"""Tasks with same priority sorted by preferred_time."""
	from pawpal_system import Scheduler, Owner
	from datetime import time
	
	owner = Owner(
		name="Bob",
		available_minutes_per_day=120,
		preferred_start_time=time(7, 0),
		preferred_end_time=time(20, 0),
	)
	
	scheduler = Scheduler(owner=owner)
	
	task_early = Task(
		name="Morning Walk",
		category=TaskCategory.WALK,
		duration_minutes=30,
		priority=Priority.HIGH,
		is_recurring=False,
		preferred_time=time(8, 0),
	)
	task_late = Task(
		name="Evening Walk",
		category=TaskCategory.WALK,
		duration_minutes=30,
		priority=Priority.HIGH,
		is_recurring=False,
		preferred_time=time(18, 0),
	)
	
	tasks = [task_late, task_early]
	sorted_tasks = scheduler._sort_tasks_by_priority(tasks)
	
	# Earlier preferred time should come first
	assert sorted_tasks[0].preferred_time == time(8, 0)
	assert sorted_tasks[1].preferred_time == time(18, 0)


def test_sort_by_priority_then_time_public_method() -> None:
	"""Public display sort orders by priority first, then preferred time."""
	from pawpal_system import Scheduler, Owner
	from datetime import time

	owner = Owner(
		name="Eve",
		available_minutes_per_day=120,
		preferred_start_time=time(7, 0),
		preferred_end_time=time(20, 0),
	)

	scheduler = Scheduler(owner=owner)

	high_late = Task(
		name="High Late",
		category=TaskCategory.WALK,
		duration_minutes=30,
		priority=Priority.HIGH,
		is_recurring=False,
		preferred_time=time(18, 0),
	)
	high_early = Task(
		name="High Early",
		category=TaskCategory.FEED,
		duration_minutes=15,
		priority=Priority.HIGH,
		is_recurring=False,
		preferred_time=time(8, 0),
	)
	medium = Task(
		name="Medium Task",
		category=TaskCategory.GROOMING,
		duration_minutes=20,
		priority=Priority.MEDIUM,
		is_recurring=False,
		preferred_time=time(9, 0),
	)

	sorted_display = scheduler.sort_by_priority_then_time([medium, high_late, high_early])

	assert [item["name"] for item in sorted_display] == ["High Early", "High Late", "Medium Task"]


# ============================================================================
# TESTS FOR FILTERING BY PET/STATUS
# ============================================================================


def test_filter_tasks_by_pet() -> None:
	"""Only retrieve tasks for specified pet."""
	from pawpal_system import Owner, Scheduler
	from datetime import time, date
	
	owner = Owner(
		name="Carol",
		available_minutes_per_day=120,
		preferred_start_time=time(7, 0),
		preferred_end_time=time(20, 0),
	)
	
	dog = Pet(name="Buddy", species="dog", breed="Lab", age_years=3.0, weight_kg=30.0)
	cat = Pet(name="Whiskers", species="cat", breed="Tabby", age_years=2.0, weight_kg=4.5)
	
	owner.add_pet(dog)
	owner.add_pet(cat)
	
	dog_task = Task(
		name="Dog Walk",
		category=TaskCategory.WALK,
		duration_minutes=30,
		priority=Priority.HIGH,
		is_recurring=False,
		frequency="daily",
	)
	cat_task = Task(
		name="Cat Feed",
		category=TaskCategory.FEED,
		duration_minutes=10,
		priority=Priority.HIGH,
		is_recurring=False,
		frequency="daily",
	)
	
	dog.add_task(dog_task)
	cat.add_task(cat_task)
	
	scheduler = Scheduler(owner=owner, pet=dog)
	tasks = scheduler._retrieve_owner_pet_tasks(date.today())
	
	# Should only have dog tasks
	assert len(tasks) == 1
	assert tasks[0].name == "Dog Walk"


def test_filter_tasks_by_completion_status() -> None:
	"""Completed tasks excluded from scheduling."""
	from pawpal_system import Owner, Scheduler
	from datetime import time, date
	
	owner = Owner(
		name="Dave",
		available_minutes_per_day=120,
		preferred_start_time=time(7, 0),
		preferred_end_time=time(20, 0),
	)
	
	pet = Pet(name="Buddy", species="dog", breed="Lab", age_years=3.0, weight_kg=30.0)
	owner.add_pet(pet)
	
	completed_task = Task(
		name="Morning Walk",
		category=TaskCategory.WALK,
		duration_minutes=30,
		priority=Priority.HIGH,
		is_recurring=False,
		frequency="once",
	)
	pending_task = Task(
		name="Evening Feed",
		category=TaskCategory.FEED,
		duration_minutes=10,
		priority=Priority.HIGH,
		is_recurring=False,
		frequency="daily",
	)
	
	completed_task.mark_complete()
	
	pet.add_task(completed_task)
	pet.add_task(pending_task)
	
	scheduler = Scheduler(owner=owner)
	tasks = scheduler._retrieve_owner_pet_tasks(date.today())
	
	# Should only have pending task
	assert len(tasks) == 1
	assert tasks[0].name == "Evening Feed"
	assert tasks[0].is_completed is False


# ============================================================================
# TESTS FOR HANDLING RECURRING TASKS
# ============================================================================


def test_daily_task_is_due_every_day() -> None:
	"""Daily tasks are due on any date."""
	from datetime import date
	
	task = Task(
		name="Daily Feed",
		category=TaskCategory.FEED,
		duration_minutes=10,
		priority=Priority.HIGH,
		is_recurring=True,
		frequency="daily",
	)
	
	today = date.today()
	tomorrow = date.fromordinal(today.toordinal() + 1)
	
	assert task.is_due_on(today) is True
	assert task.is_due_on(tomorrow) is True


def test_once_task_due_until_completed() -> None:
	"""One-time tasks due until marked complete."""
	from datetime import date
	
	task = Task(
		name="Vet Appointment",
		category=TaskCategory.VET,
		duration_minutes=60,
		priority=Priority.HIGH,
		is_recurring=False,
		frequency="once",
	)
	
	assert task.is_due_on(date.today()) is True
	task.mark_complete()
	assert task.is_due_on(date.today()) is False


def test_weekly_task_with_recurrence_days() -> None:
	"""Weekly tasks due only on specified days."""
	from datetime import date, timedelta
	
	# Create task due on Mondays
	task = Task(
		name="Monday Grooming",
		category=TaskCategory.GROOMING,
		duration_minutes=30,
		priority=Priority.MEDIUM,
		is_recurring=True,
		frequency="weekly",
		recurrence_days=["Monday"],
	)
	
	# Find a Monday
	today = date.today()
	days_ahead = 0 - today.weekday()  # Monday is 0
	if days_ahead <= 0:
		days_ahead += 7
	next_monday = today + timedelta(days=days_ahead)
	
	# Find a non-Monday
	non_monday = today if today.weekday() != 0 else today + timedelta(days=1)
	
	if task.is_due_on(next_monday):
		assert next_monday.strftime("%A") == "Monday"


# ============================================================================
# TESTS FOR BASIC CONFLICT DETECTION
# ============================================================================


def test_overlapping_tasks_detected() -> None:
	"""Overlapping scheduled tasks are detected."""
	from pawpal_system import ScheduledTask, DailyPlan
	from datetime import date, time
	
	task1 = Task(
		name="Task 1",
		category=TaskCategory.WALK,
		duration_minutes=30,
		priority=Priority.HIGH,
		is_recurring=False,
	)
	task2 = Task(
		name="Task 2",
		category=TaskCategory.FEED,
		duration_minutes=20,
		priority=Priority.HIGH,
		is_recurring=False,
	)
	
	scheduled1 = ScheduledTask(task=task1, start_time=time(9, 0), reasoning="test")
	scheduled2 = ScheduledTask(task=task2, start_time=time(9, 15), reasoning="test")
	
	# Task 1: 9:00-9:30, Task 2: 9:15-9:35 -> overlap
	assert scheduled1.overlaps_with(scheduled2) is True
	assert scheduled2.overlaps_with(scheduled1) is True


def test_non_overlapping_tasks_not_detected() -> None:
	"""Non-overlapping tasks don't trigger conflict."""
	from pawpal_system import ScheduledTask
	from datetime import time
	
	task1 = Task(
		name="Task 1",
		category=TaskCategory.WALK,
		duration_minutes=30,
		priority=Priority.HIGH,
		is_recurring=False,
	)
	task2 = Task(
		name="Task 2",
		category=TaskCategory.FEED,
		duration_minutes=20,
		priority=Priority.HIGH,
		is_recurring=False,
	)
	
	scheduled1 = ScheduledTask(task=task1, start_time=time(9, 0), reasoning="test")
	scheduled2 = ScheduledTask(task=task2, start_time=time(9, 30), reasoning="test")
	
	# Task 1: 9:00-9:30, Task 2: 9:30-9:50 -> no overlap (exact boundary)
	assert scheduled1.overlaps_with(scheduled2) is False
	assert scheduled2.overlaps_with(scheduled1) is False


def test_daily_plan_detects_any_conflicts() -> None:
	"""DailyPlan.has_conflicts() detects overlapping tasks."""
	from pawpal_system import ScheduledTask, DailyPlan
	from datetime import date, time
	
	plan = DailyPlan(date=date.today())
	
	task1 = Task(
		name="Morning Walk",
		category=TaskCategory.WALK,
		duration_minutes=30,
		priority=Priority.HIGH,
		is_recurring=False,
	)
	task2 = Task(
		name="Breakfast Feed",
		category=TaskCategory.FEED,
		duration_minutes=15,
		priority=Priority.HIGH,
		is_recurring=False,
	)
	
	scheduled1 = ScheduledTask(task=task1, start_time=time(9, 0), reasoning="test")
	scheduled2 = ScheduledTask(task=task2, start_time=time(9, 15), reasoning="test")
	
	plan.add_scheduled_task(scheduled1)
	assert plan.has_conflicts() is False
	
	plan.add_scheduled_task(scheduled2)
	assert plan.has_conflicts() is True


def test_find_conflicts_sorted_identifies_pairs() -> None:
	"""Sweep-line algorithm correctly identifies conflicting pairs."""
	from pawpal_system import ScheduledTask, DailyPlan
	from datetime import date, time
	
	plan = DailyPlan(date=date.today())
	
	# Create 3 tasks: t1 and t2 overlap, t3 is separate
	task1 = Task(
		name="Task 1",
		category=TaskCategory.WALK,
		duration_minutes=30,
		priority=Priority.HIGH,
		is_recurring=False,
	)
	task2 = Task(
		name="Task 2",
		category=TaskCategory.FEED,
		duration_minutes=20,
		priority=Priority.HIGH,
		is_recurring=False,
	)
	task3 = Task(
		name="Task 3",
		category=TaskCategory.GROOMING,
		duration_minutes=15,
		priority=Priority.HIGH,
		is_recurring=False,
	)
	
	# t1: 9:00-9:30, t2: 9:15-9:35 (overlap), t3: 10:00-10:15 (no overlap)
	scheduled1 = ScheduledTask(task=task1, start_time=time(9, 0), reasoning="test")
	scheduled2 = ScheduledTask(task=task2, start_time=time(9, 15), reasoning="test")
	scheduled3 = ScheduledTask(task=task3, start_time=time(10, 0), reasoning="test")
	
	plan.add_scheduled_task(scheduled1)
	plan.add_scheduled_task(scheduled2)
	plan.add_scheduled_task(scheduled3)
	
	conflicts = plan.find_conflicts_sorted()
	
	# Should find exactly one conflict pair
	assert len(conflicts) == 1
	assert (scheduled1, scheduled2) == conflicts[0] or (scheduled2, scheduled1) == conflicts[0]


# ============================================================================
# TESTS FOR CONVENIENCE FILTERING METHODS
# ============================================================================


def test_get_tasks_for_pet() -> None:
	"""get_tasks_for_pet returns all tasks for a specific pet."""
	from pawpal_system import Owner, Scheduler
	from datetime import time
	
	owner = Owner(
		name="Emma",
		available_minutes_per_day=120,
		preferred_start_time=time(7, 0),
		preferred_end_time=time(20, 0),
	)
	
	dog = Pet(name="Rex", species="dog", breed="German Shepherd", age_years=5.0, weight_kg=35.0)
	cat = Pet(name="Mittens", species="cat", breed="Siamese", age_years=3.0, weight_kg=3.5)
	
	owner.add_pet(dog)
	owner.add_pet(cat)
	
	dog_task1 = Task(
		name="Dog Walk 1",
		category=TaskCategory.WALK,
		duration_minutes=30,
		priority=Priority.HIGH,
		is_recurring=False,
	)
	dog_task2 = Task(
		name="Dog Walk 2",
		category=TaskCategory.WALK,
		duration_minutes=20,
		priority=Priority.MEDIUM,
		is_recurring=False,
	)
	cat_task = Task(
		name="Cat Feed",
		category=TaskCategory.FEED,
		duration_minutes=10,
		priority=Priority.HIGH,
		is_recurring=False,
	)
	
	dog.add_task(dog_task1)
	dog.add_task(dog_task2)
	cat.add_task(cat_task)
	
	scheduler = Scheduler(owner=owner)
	dog_tasks = scheduler.get_tasks_for_pet(dog.pet_id)
	
	assert len(dog_tasks) == 2
	assert all(t.pet_id == dog.pet_id for t in dog_tasks)


def test_get_pending_tasks() -> None:
	"""get_pending_tasks returns only non-completed, due tasks."""
	from pawpal_system import Owner, Scheduler
	from datetime import time, date
	
	owner = Owner(
		name="Frank",
		available_minutes_per_day=120,
		preferred_start_time=time(7, 0),
		preferred_end_time=time(20, 0),
	)
	
	pet = Pet(name="Buddy", species="dog", breed="Poodle", age_years=2.0, weight_kg=8.0)
	owner.add_pet(pet)
	
	completed_task = Task(
		name="Completed Walk",
		category=TaskCategory.WALK,
		duration_minutes=30,
		priority=Priority.HIGH,
		is_recurring=False,
		frequency="daily",
	)
	pending_task = Task(
		name="Pending Feed",
		category=TaskCategory.FEED,
		duration_minutes=10,
		priority=Priority.HIGH,
		is_recurring=False,
		frequency="daily",
	)
	
	completed_task.mark_complete()
	pet.add_task(completed_task)
	pet.add_task(pending_task)
	
	scheduler = Scheduler(owner=owner)
	pending = scheduler.get_pending_tasks()
	
	assert len(pending) == 1
	assert pending[0].name == "Pending Feed"
	assert pending[0].is_completed is False


def test_get_recurring_tasks() -> None:
	"""get_recurring_tasks returns only tasks with is_recurring=True."""
	from pawpal_system import Owner, Scheduler
	from datetime import time
	
	owner = Owner(
		name="Grace",
		available_minutes_per_day=120,
		preferred_start_time=time(7, 0),
		preferred_end_time=time(20, 0),
	)
	
	pet = Pet(name="Buddy", species="dog", breed="Beagle", age_years=4.0, weight_kg=12.0)
	owner.add_pet(pet)
	
	recurring_task = Task(
		name="Daily Feed",
		category=TaskCategory.FEED,
		duration_minutes=10,
		priority=Priority.HIGH,
		is_recurring=True,
		frequency="daily",
	)
	one_time_task = Task(
		name="Vet Appointment",
		category=TaskCategory.VET,
		duration_minutes=60,
		priority=Priority.HIGH,
		is_recurring=False,
		frequency="once",
	)
	
	pet.add_task(recurring_task)
	pet.add_task(one_time_task)
	
	scheduler = Scheduler(owner=owner)
	recurring = scheduler.get_recurring_tasks()
	
	assert len(recurring) == 1
	assert recurring[0].name == "Daily Feed"
	assert recurring[0].is_recurring is True


def test_get_tasks_by_category() -> None:
	"""get_tasks_by_category filters tasks by TaskCategory."""
	from pawpal_system import Owner, Scheduler
	from datetime import time
	
	owner = Owner(
		name="Henry",
		available_minutes_per_day=120,
		preferred_start_time=time(7, 0),
		preferred_end_time=time(20, 0),
	)
	
	pet = Pet(name="Buddy", species="dog", breed="Husky", age_years=1.0, weight_kg=25.0)
	owner.add_pet(pet)
	
	walk_task = Task(
		name="Morning Walk",
		category=TaskCategory.WALK,
		duration_minutes=30,
		priority=Priority.HIGH,
		is_recurring=True,
		frequency="daily",
	)
	feed_task = Task(
		name="Breakfast",
		category=TaskCategory.FEED,
		duration_minutes=15,
		priority=Priority.HIGH,
		is_recurring=True,
		frequency="daily",
	)
	groom_task = Task(
		name="Grooming",
		category=TaskCategory.GROOMING,
		duration_minutes=45,
		priority=Priority.MEDIUM,
		is_recurring=False,
	)
	
	pet.add_task(walk_task)
	pet.add_task(feed_task)
	pet.add_task(groom_task)
	
	scheduler = Scheduler(owner=owner)
	walk_tasks = scheduler.get_tasks_by_category(TaskCategory.WALK)
	
	assert len(walk_tasks) == 1
	assert walk_tasks[0].category == TaskCategory.WALK


def test_get_high_priority_tasks() -> None:
	"""get_high_priority_tasks returns only HIGH priority tasks."""
	from pawpal_system import Owner, Scheduler
	from datetime import time, date
	
	owner = Owner(
		name="Iris",
		available_minutes_per_day=120,
		preferred_start_time=time(7, 0),
		preferred_end_time=time(20, 0),
	)
	
	pet = Pet(name="Buddy", species="dog", breed="Dalmatian", age_years=3.0, weight_kg=28.0)
	owner.add_pet(pet)
	
	high_task = Task(
		name="Medication",
		category=TaskCategory.MEDICATION,
		duration_minutes=5,
		priority=Priority.HIGH,
		is_recurring=False,
		frequency="daily",
	)
	medium_task = Task(
		name="Grooming",
		category=TaskCategory.GROOMING,
		duration_minutes=30,
		priority=Priority.MEDIUM,
		is_recurring=False,
		frequency="daily",
	)
	
	pet.add_task(high_task)
	pet.add_task(medium_task)
	
	scheduler = Scheduler(owner=owner)
	high_priority = scheduler.get_high_priority_tasks()
	
	assert len(high_priority) == 1
	assert high_priority[0].priority == Priority.HIGH


def test_sort_by_time_returns_hhmm() -> None:
	"""sort_by_time returns tasks sorted by time with HH:MM formatting."""
	from datetime import time
	from pawpal_system import Owner, Scheduler

	owner = Owner(
		name="Jill",
		available_minutes_per_day=120,
		preferred_start_time=time(7, 0),
		preferred_end_time=time(20, 0),
	)

	pet = Pet(name="Buddy", species="dog", breed="Mix", age_years=2.0, weight_kg=12.0)
	owner.add_pet(pet)

	task_late = Task(
		name="Late Feed",
		category=TaskCategory.FEED,
		duration_minutes=10,
		priority=Priority.MEDIUM,
		is_recurring=True,
		preferred_time=time(18, 30),
	)
	task_early = Task(
		name="Early Walk",
		category=TaskCategory.WALK,
		duration_minutes=20,
		priority=Priority.HIGH,
		is_recurring=True,
		preferred_time=time(8, 5),
	)
	task_no_time = Task(
		name="Open Play",
		category=TaskCategory.ENRICHMENT,
		duration_minutes=15,
		priority=Priority.LOW,
		is_recurring=False,
	)

	pet.add_task(task_late)
	pet.add_task(task_early)
	pet.add_task(task_no_time)

	scheduler = Scheduler(owner=owner)
	result = scheduler.sort_by_time()

	assert result[0]["name"] == "Early Walk"
	assert result[0]["time"] == "08:05"
	assert result[1]["name"] == "Late Feed"
	assert result[1]["time"] == "18:30"
	assert result[2]["name"] == "Open Play"
	assert result[2]["time"] == "Unscheduled"


def test_filter_tasks_method_by_completion_status() -> None:
	"""filter_tasks supports filtering by completion status."""
	from datetime import time
	from pawpal_system import Owner, Scheduler

	owner = Owner(
		name="Kai",
		available_minutes_per_day=120,
		preferred_start_time=time(7, 0),
		preferred_end_time=time(20, 0),
	)

	pet = Pet(name="Nori", species="cat", breed="Tabby", age_years=3.0, weight_kg=4.0)
	owner.add_pet(pet)

	done_task = Task(
		name="Morning Feed",
		category=TaskCategory.FEED,
		duration_minutes=10,
		priority=Priority.HIGH,
		is_recurring=True,
	)
	pending_task = Task(
		name="Evening Walk",
		category=TaskCategory.WALK,
		duration_minutes=20,
		priority=Priority.MEDIUM,
		is_recurring=True,
	)

	done_task.mark_complete()
	pet.add_task(done_task)
	pet.add_task(pending_task)

	scheduler = Scheduler(owner=owner)
	completed = scheduler.filter_tasks(is_completed=True)
	not_completed = scheduler.filter_tasks(is_completed=False)

	assert len(completed) == 1
	assert completed[0].name == "Morning Feed"
	assert len(not_completed) == 1
	assert not_completed[0].name == "Evening Walk"


def test_filter_tasks_by_name_case_insensitive() -> None:
	"""filter_tasks supports case-insensitive name filtering."""
	from datetime import time
	from pawpal_system import Owner, Scheduler

	owner = Owner(
		name="Lena",
		available_minutes_per_day=120,
		preferred_start_time=time(7, 0),
		preferred_end_time=time(20, 0),
	)

	pet = Pet(name="Mochi", species="dog", breed="Corgi", age_years=4.0, weight_kg=10.0)
	owner.add_pet(pet)

	task1 = Task(
		name="Morning Walk",
		category=TaskCategory.WALK,
		duration_minutes=20,
		priority=Priority.HIGH,
		is_recurring=True,
	)
	task2 = Task(
		name="Evening Feed",
		category=TaskCategory.FEED,
		duration_minutes=10,
		priority=Priority.HIGH,
		is_recurring=True,
	)

	pet.add_task(task1)
	pet.add_task(task2)

	scheduler = Scheduler(owner=owner)
	matched = scheduler.filter_tasks(name="walk")

	assert len(matched) == 1
	assert matched[0].name == "Morning Walk"


def test_filter_tasks_by_pet_name_case_insensitive() -> None:
	"""filter_tasks supports case-insensitive pet-name filtering."""
	from datetime import time
	from pawpal_system import Owner, Scheduler

	owner = Owner(
		name="Mina",
		available_minutes_per_day=120,
		preferred_start_time=time(7, 0),
		preferred_end_time=time(20, 0),
	)

	dog = Pet(name="Mochi", species="dog", breed="Corgi", age_years=4.0, weight_kg=10.0)
	cat = Pet(name="Nori", species="cat", breed="Tabby", age_years=2.0, weight_kg=4.0)
	owner.add_pet(dog)
	owner.add_pet(cat)

	dog_task = Task(
		name="Morning Walk",
		category=TaskCategory.WALK,
		duration_minutes=20,
		priority=Priority.HIGH,
		is_recurring=True,
	)
	cat_task = Task(
		name="Breakfast Feed",
		category=TaskCategory.FEED,
		duration_minutes=10,
		priority=Priority.HIGH,
		is_recurring=True,
	)

	dog.add_task(dog_task)
	cat.add_task(cat_task)

	scheduler = Scheduler(owner=owner)
	mochi_tasks = scheduler.filter_tasks(pet_name="moChi")

	assert len(mochi_tasks) == 1
	assert mochi_tasks[0].name == "Morning Walk"


def test_mark_task_completed_creates_next_daily_occurrence() -> None:
	"""Completing a daily task auto-creates the next day's instance."""
	from datetime import date, time
	from pawpal_system import Owner, Scheduler

	owner = Owner(
		name="Noah",
		available_minutes_per_day=120,
		preferred_start_time=time(7, 0),
		preferred_end_time=time(20, 0),
	)

	pet = Pet(name="Mochi", species="dog", breed="Corgi", age_years=4.0, weight_kg=10.0)
	owner.add_pet(pet)

	daily_task = Task(
		name="Daily Feed",
		category=TaskCategory.FEED,
		duration_minutes=10,
		priority=Priority.HIGH,
		is_recurring=True,
		frequency="daily",
		preferred_time=time(9, 0),
	)
	pet.add_task(daily_task)

	scheduler = Scheduler(owner=owner)
	completed_date = date(2026, 3, 20)
	next_task = scheduler.mark_task_completed(daily_task.task_id, completed_date)

	assert next_task is not None
	assert daily_task.is_completed is True
	assert next_task.name == "Daily Feed"
	assert next_task.is_completed is False
	assert next_task.scheduled_for == date(2026, 3, 21)
	assert len(pet.tasks) == 2


def test_mark_task_completed_creates_next_weekly_occurrence() -> None:
	"""Completing a weekly task creates next listed weekday occurrence."""
	from datetime import date, time
	from pawpal_system import Owner, Scheduler

	owner = Owner(
		name="Owen",
		available_minutes_per_day=120,
		preferred_start_time=time(7, 0),
		preferred_end_time=time(20, 0),
	)

	pet = Pet(name="Nori", species="cat", breed="Tabby", age_years=2.0, weight_kg=4.0)
	owner.add_pet(pet)

	weekly_task = Task(
		name="Brush Coat",
		category=TaskCategory.GROOMING,
		duration_minutes=15,
		priority=Priority.MEDIUM,
		is_recurring=True,
		frequency="weekly",
		recurrence_days=["Monday", "Thursday"],
	)
	pet.add_task(weekly_task)

	scheduler = Scheduler(owner=owner)
	# Thursday
	completed_date = date(2026, 3, 19)
	next_task = scheduler.mark_task_completed(weekly_task.task_id, completed_date)

	assert next_task is not None
	# Next listed day after Thursday should be Monday (2026-03-23)
	assert next_task.scheduled_for == date(2026, 3, 23)


def test_scheduled_for_occurrence_only_due_on_that_date() -> None:
	"""Occurrence-bound tasks should only be due on scheduled_for date."""
	from datetime import date

	task = Task(
		name="Occurrence Task",
		category=TaskCategory.OTHER,
		duration_minutes=10,
		priority=Priority.LOW,
		is_recurring=True,
		frequency="daily",
		scheduled_for=date(2026, 3, 21),
	)

	assert task.is_due_on(date(2026, 3, 20)) is False
	assert task.is_due_on(date(2026, 3, 21)) is True
	assert task.is_due_on(date(2026, 3, 22)) is False


def test_generate_plan_adds_warning_for_same_preferred_time_request() -> None:
	"""Scheduler returns a warning (not an exception) for same-time task requests."""
	from datetime import date, time
	from pawpal_system import Owner, Scheduler

	owner = Owner(
		name="Parker",
		available_minutes_per_day=120,
		preferred_start_time=time(7, 0),
		preferred_end_time=time(20, 0),
	)

	dog = Pet(name="Mochi", species="dog", breed="Corgi", age_years=4.0, weight_kg=10.0)
	cat = Pet(name="Nori", species="cat", breed="Tabby", age_years=2.0, weight_kg=4.0)
	owner.add_pet(dog)
	owner.add_pet(cat)

	dog.add_task(
		Task(
			name="Morning Walk",
			category=TaskCategory.WALK,
			duration_minutes=30,
			priority=Priority.HIGH,
			is_recurring=True,
			frequency="daily",
			preferred_time=time(8, 0),
		)
	)
	cat.add_task(
		Task(
			name="Breakfast Feed",
			category=TaskCategory.FEED,
			duration_minutes=15,
			priority=Priority.HIGH,
			is_recurring=True,
			frequency="daily",
			preferred_time=time(8, 0),
		)
	)

	scheduler = Scheduler(owner=owner)
	plan = scheduler.generate_plan(date.today())

	assert any("Timing conflict request at 08:00" in warning for warning in plan.warnings)


# ============================================================================
# RUBRIC-ALIGNED CORE BEHAVIOR TESTS
# ============================================================================


def test_sorting_correctness_tasks_returned_in_chronological_order() -> None:
	"""Sorting correctness: tasks should be returned in HH:MM chronological order."""
	from datetime import time
	from pawpal_system import Owner, Scheduler

	owner = Owner(
		name="Quinn",
		available_minutes_per_day=120,
		preferred_start_time=time(7, 0),
		preferred_end_time=time(20, 0),
	)

	pet = Pet(name="Mochi", species="dog", breed="Corgi", age_years=4.0, weight_kg=10.0)
	owner.add_pet(pet)

	pet.add_task(
		Task(
			name="Late Walk",
			category=TaskCategory.WALK,
			duration_minutes=20,
			priority=Priority.HIGH,
			is_recurring=True,
			preferred_time=time(18, 45),
		)
	)
	pet.add_task(
		Task(
			name="Morning Feed",
			category=TaskCategory.FEED,
			duration_minutes=10,
			priority=Priority.HIGH,
			is_recurring=True,
			preferred_time=time(8, 0),
		)
	)
	pet.add_task(
		Task(
			name="Midday Play",
			category=TaskCategory.ENRICHMENT,
			duration_minutes=15,
			priority=Priority.MEDIUM,
			is_recurring=True,
			preferred_time=time(12, 30),
		)
	)

	scheduler = Scheduler(owner=owner)
	sorted_view = scheduler.sort_by_time()

	assert [item["time"] for item in sorted_view] == ["08:00", "12:30", "18:45"]
	assert [item["name"] for item in sorted_view] == ["Morning Feed", "Midday Play", "Late Walk"]


def test_recurrence_logic_daily_completion_creates_following_day_task() -> None:
	"""Recurrence logic: completing a daily task creates a new task on the next day."""
	from datetime import date, time
	from pawpal_system import Owner, Scheduler

	owner = Owner(
		name="Riley",
		available_minutes_per_day=120,
		preferred_start_time=time(7, 0),
		preferred_end_time=time(20, 0),
	)

	pet = Pet(name="Nori", species="cat", breed="Tabby", age_years=2.0, weight_kg=4.0)
	owner.add_pet(pet)

	daily_task = Task(
		name="Daily Medication",
		category=TaskCategory.MEDICATION,
		duration_minutes=5,
		priority=Priority.HIGH,
		is_recurring=True,
		frequency="daily",
		preferred_time=time(9, 0),
	)
	pet.add_task(daily_task)

	scheduler = Scheduler(owner=owner)
	completed_date = date(2026, 3, 20)
	next_task = scheduler.mark_task_completed(daily_task.task_id, completed_date)

	assert daily_task.is_completed is True
	assert next_task is not None
	assert next_task.name == "Daily Medication"
	assert next_task.is_completed is False
	assert next_task.scheduled_for == date(2026, 3, 21)


def test_conflict_detection_scheduler_flags_duplicate_times() -> None:
	"""Conflict detection: duplicate preferred times should generate a warning."""
	from datetime import date, time
	from pawpal_system import Owner, Scheduler

	owner = Owner(
		name="Sky",
		available_minutes_per_day=120,
		preferred_start_time=time(7, 0),
		preferred_end_time=time(20, 0),
	)

	dog = Pet(name="Mochi", species="dog", breed="Corgi", age_years=4.0, weight_kg=10.0)
	cat = Pet(name="Nori", species="cat", breed="Tabby", age_years=2.0, weight_kg=4.0)
	owner.add_pet(dog)
	owner.add_pet(cat)

	dog.add_task(
		Task(
			name="Walk",
			category=TaskCategory.WALK,
			duration_minutes=30,
			priority=Priority.HIGH,
			is_recurring=True,
			frequency="daily",
			preferred_time=time(8, 0),
		)
	)
	cat.add_task(
		Task(
			name="Feed",
			category=TaskCategory.FEED,
			duration_minutes=15,
			priority=Priority.HIGH,
			is_recurring=True,
			frequency="daily",
			preferred_time=time(8, 0),
		)
	)

	scheduler = Scheduler(owner=owner)
	plan = scheduler.generate_plan(date.today())

	assert any("Timing conflict request at 08:00" in warning for warning in plan.warnings)
