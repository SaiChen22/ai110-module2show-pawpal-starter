from __future__ import annotations

from datetime import date, time

from pawpal_system import Owner, Pet, Priority, Scheduler, Task, TaskCategory


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

	# At least three tasks with different preferred times.
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
			name="Breakfast Feed",
			category=TaskCategory.FEED,
			duration_minutes=15,
			priority=Priority.HIGH,
			is_recurring=True,
			frequency="daily",
			preferred_time=time(9, 0),
		)
	)
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
		for idx, scheduled in enumerate(plan.scheduled_tasks, start=1):
			pet_name = pet_name_by_id.get(scheduled.task.pet_id, "Unknown Pet")
			print(
				f"{idx}. {scheduled.start_time.strftime('%H:%M')} - "
				f"{scheduled.end_time.strftime('%H:%M')} | "
				f"{scheduled.task.name} ({pet_name}) "
				f"[{scheduled.task.priority.name}]"
			)
			print(f"   Reason: {scheduled.reasoning}")

	if plan.unscheduled_tasks:
		print()
		print("Unscheduled Tasks")
		print("-" * 50)
		for task in plan.unscheduled_tasks:
			pet_name = pet_name_by_id.get(task.pet_id, "Unknown Pet")
			print(
				f"- {task.name} ({pet_name}) "
				f"[{task.priority.name}, {task.duration_minutes} min]"
			)

	if plan.warnings:
		print()
		print("Warnings")
		print("-" * 50)
		for warning in plan.warnings:
			print(f"- {warning}")


if __name__ == "__main__":
	scheduler = build_sample_scheduler()
	print_today_schedule(scheduler)
