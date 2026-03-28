from __future__ import annotations

from datetime import date, time

from pawpal_system import Owner, Pet, Priority, Scheduler, Task, TaskCategory
from tabulate import tabulate


PRIORITY_BADGES = {
	"HIGH": "🔴 High",
	"MEDIUM": "🟡 Medium",
	"LOW": "🟢 Low",
}

CATEGORY_BADGES = {
	"walk": "🐕 Walk",
	"feed": "🍽️ Feed",
	"medication": "💊 Medication",
	"grooming": "🛁 Grooming",
	"enrichment": "🎾 Enrichment",
	"vet": "🩺 Vet",
	"other": "📌 Other",
}


def _priority_badge(priority: Priority) -> str:
	return PRIORITY_BADGES.get(priority.name, priority.name.title())


def _category_badge(category: TaskCategory) -> str:
	return CATEGORY_BADGES.get(category.value, category.value.title())


def build_sample_scheduler() -> Scheduler:
	owner = Owner(
		name="Jordan",
		available_minutes_per_day=120,
		preferred_start_time=time(7, 0),
		preferred_end_time=time(20, 0),
		notes="Weekday routine",
	)

	dog = Pet(
		name="Mochi",
		species="dog",
		breed="Corgi Mix",
		age_years=4.0,
		weight_kg=11.5,
	)
	cat = Pet(
		name="Nori",
		species="cat",
		breed="Tabby",
		age_years=2.0,
		weight_kg=4.8,
	)

	owner.add_pet(dog)
	owner.add_pet(cat)

	# Add tasks intentionally out of chronological order to validate sorting behavior.
	dog.add_task(
		Task(
			name="Evening Grooming",
			category=TaskCategory.GROOMING,
			duration_minutes=20,
			priority=Priority.MEDIUM,
			is_recurring=True,
			frequency="daily",
			preferred_time=time(18, 0),
		)
	)
	dog.add_task(
		Task(
			name="Morning Walk",
			category=TaskCategory.WALK,
			duration_minutes=30,
			priority=Priority.HIGH,
			is_recurring=True,
			frequency="daily",
			preferred_time=time(8, 0),
			notes="Neighborhood route",
		)
	)
	cat.add_task(
		Task(
			name="Midday Play",
			category=TaskCategory.ENRICHMENT,
			duration_minutes=20,
			priority=Priority.LOW,
			is_recurring=True,
			frequency="daily",
			preferred_time=time(12, 0),
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
	cat.add_task(
		Task(
			name="Anytime Litter Check",
			category=TaskCategory.OTHER,
			duration_minutes=10,
			priority=Priority.MEDIUM,
			is_recurring=True,
			frequency="daily",
		)
	)

	# Mark one task complete so completion-status filtering can be demonstrated.
	for task in owner.get_all_tasks():
		if task.name == "Midday Play":
			task.mark_complete()
			break

	return Scheduler(owner=owner)


def print_today_schedule(scheduler: Scheduler) -> None:
	today = date.today()
	plan = scheduler.generate_plan(today)
	pet_name_by_id = {pet.pet_id: pet.name for pet in scheduler.owner.pets}

	print("Today's Schedule")
	print("=" * 50)
	print(f"Date: {today.isoformat()}")
	print(f"Owner: {scheduler.owner.name}")
	print(f"Total scheduled minutes: {plan.total_minutes_scheduled}")
	print()

	if not plan.scheduled_tasks:
		print("No tasks could be scheduled.")
	else:
		rows = []
		for scheduled in plan.scheduled_tasks:
			pet_name = pet_name_by_id.get(scheduled.task.pet_id, "Unknown Pet")
			rows.append(
				[
					f"{scheduled.start_time.strftime('%H:%M')} - {scheduled.end_time.strftime('%H:%M')}",
					scheduled.task.name,
					pet_name,
					_category_badge(scheduled.task.category),
					_priority_badge(scheduled.task.priority),
					scheduled.task.duration_minutes,
					scheduled.reasoning,
				]
			)
		print(tabulate(rows, headers=["Time", "Task", "Pet", "Category", "Priority", "Min", "Reasoning"], tablefmt="github"))

	if plan.unscheduled_tasks:
		print()
		print("Unscheduled Tasks")
		print("-" * 50)
		unscheduled_rows = []
		for task in plan.unscheduled_tasks:
			pet_name = pet_name_by_id.get(task.pet_id, "Unknown Pet")
			unscheduled_rows.append(
				[
					task.name,
					pet_name,
					_category_badge(task.category),
					_priority_badge(task.priority),
					task.duration_minutes,
				]
			)
		print(tabulate(unscheduled_rows, headers=["Task", "Pet", "Category", "Priority", "Min"], tablefmt="github"))

	if plan.warnings:
		print()
		print("Warnings")
		print("-" * 50)
		warning_rows = [["⚠️", warning] for warning in plan.warnings]
		print(tabulate(warning_rows, headers=["Type", "Message"], tablefmt="github"))


def print_sort_and_filter_demo(scheduler: Scheduler) -> None:
	print()
	print("Sort/Filter Demo")
	print("=" * 50)

	print("Tasks Sorted By Time (HH:MM)")
	print("-" * 50)
	sorted_rows = []
	for row in scheduler.sort_by_priority_then_time():
		task_obj = next((task for task in scheduler.owner.get_all_tasks() if task.task_id == row["task_id"]), None)
		category = _category_badge(task_obj.category) if task_obj is not None else "Unknown"
		sorted_rows.append(
			[
				row["time"],
				row["name"],
				category,
				_priority_badge(Priority[row["priority"]]),
				"✅ Completed" if row["is_completed"] else "🟠 Pending",
			]
		)
	print(tabulate(sorted_rows, headers=["Time", "Task", "Category", "Priority", "Status"], tablefmt="github"))

	print()
	print("Filtered: Completed Tasks")
	print("-" * 50)
	completed_tasks = scheduler.filter_tasks(is_completed=True)
	if not completed_tasks:
		print("(none)")
	else:
		rows = []
		for task in completed_tasks:
			time_str = task.preferred_time.strftime("%H:%M") if task.preferred_time else "Unscheduled"
			rows.append([task.name, time_str, _category_badge(task.category), _priority_badge(task.priority), "✅ Completed"])
		print(tabulate(rows, headers=["Task", "Time", "Category", "Priority", "Status"], tablefmt="github"))

	print()
	print("Filtered: Task Name Contains 'walk'")
	print("-" * 50)
	name_filtered_tasks = scheduler.filter_tasks(name="walk")
	if not name_filtered_tasks:
		print("(none)")
	else:
		rows = []
		for task in name_filtered_tasks:
			time_str = task.preferred_time.strftime("%H:%M") if task.preferred_time else "Unscheduled"
			rows.append([task.name, time_str, _category_badge(task.category), "✅ Completed" if task.is_completed else "🟠 Pending"])
		print(tabulate(rows, headers=["Task", "Time", "Category", "Status"], tablefmt="github"))

	print()
	print("Filtered: Pet Name Contains 'mochi'")
	print("-" * 50)
	pet_filtered_tasks = scheduler.filter_tasks(pet_name="mochi")
	if not pet_filtered_tasks:
		print("(none)")
	else:
		rows = []
		for task in pet_filtered_tasks:
			time_str = task.preferred_time.strftime("%H:%M") if task.preferred_time else "Unscheduled"
			rows.append([task.name, time_str, _category_badge(task.category), _priority_badge(task.priority), "Mochi"])
		print(tabulate(rows, headers=["Task", "Time", "Category", "Priority", "Pet"], tablefmt="github"))


if __name__ == "__main__":
	scheduler = build_sample_scheduler()
	print_today_schedule(scheduler)
	print_sort_and_filter_demo(scheduler)
