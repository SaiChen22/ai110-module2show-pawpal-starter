from pawpal_system import Pet, Priority, Task, TaskCategory


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
