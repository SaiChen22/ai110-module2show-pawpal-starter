from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from enum import Enum
import json
from pathlib import Path
from typing import Any
from uuid import uuid4

import pandas as pd


# ============================================================================
# CUSTOM EXCEPTIONS
# ============================================================================


class PawPalException(Exception):
	"""Base exception for PawPal system errors."""

	pass


class ValidationError(PawPalException):
	"""Raised when data validation fails."""

	pass


class TimeConstraintError(ValidationError):
	"""Raised when time-related constraints are violated."""

	pass


class DurationError(ValidationError):
	"""Raised when duration constraints are violated."""

	pass


# ============================================================================
# VALIDATION HELPERS
# ============================================================================


def _validate_time_range(start: time, end: time, field_start: str = "start_time", field_end: str = "end_time") -> None:
	"""Validate that start_time < end_time."""
	if start >= end:
		raise TimeConstraintError(
			f"Invalid time range: {field_start} ({start}) must be before {field_end} ({end})"
		)


def _validate_positive_duration(minutes: int, field_name: str = "duration_minutes") -> None:
	"""Validate that duration is positive."""
	if minutes <= 0:
		raise DurationError(f"{field_name} must be positive, got {minutes}")


def _validate_positive_float(value: float, field_name: str) -> None:
	"""Validate that a float value is positive."""
	if value <= 0:
		raise ValidationError(f"{field_name} must be positive, got {value}")


def _validate_owner_time_window(proposed_time: time, owner_start: time, owner_end: time, task_name: str = "Task") -> None:
	"""Validate that proposed_time falls within owner's preferred window."""
	if not (owner_start <= proposed_time <= owner_end):
		raise TimeConstraintError(
			f"{task_name} scheduled at {proposed_time} is outside owner's preferred window "
			f"({owner_start} to {owner_end})"
		)


class Priority(Enum):
	HIGH = 3
	MEDIUM = 2
	LOW = 1


class TaskCategory(Enum):
	WALK = "walk"
	FEED = "feed"
	MEDICATION = "medication"
	GROOMING = "grooming"
	ENRICHMENT = "enrichment"
	VET = "vet"
	OTHER = "other"


def _parse_time(value: str) -> time:
	return time.fromisoformat(value)


def _parse_bool(value: Any) -> bool:
	if isinstance(value, bool):
		return value
	if isinstance(value, str):
		return value.strip().lower() in {"true", "1", "yes", "y"}
	if isinstance(value, (int, float)):
		return bool(value)
	return False


def _parse_date(value: str) -> date:
	return date.fromisoformat(value)


def _time_to_str(value: time) -> str:
	return value.isoformat()


def _date_to_str(value: date) -> str:
	return value.isoformat()


def _add_minutes_to_time(start: time, minutes: int) -> time:
	dt = datetime.combine(date.today(), start) + timedelta(minutes=minutes)
	return dt.time().replace(microsecond=0)


def _slot_end_within_bounds(start: time, duration_minutes: int, bound_end: time) -> bool:
	start_dt = datetime.combine(date.today(), start)
	end_dt = start_dt + timedelta(minutes=duration_minutes)
	bound_dt = datetime.combine(date.today(), bound_end)
	return end_dt <= bound_dt


@dataclass
class Owner:
	name: str
	available_minutes_per_day: int
	preferred_start_time: time
	preferred_end_time: time
	notes: str = ""
	owner_id: str = field(default_factory=lambda: str(uuid4()))
	pets: list[Pet] = field(default_factory=list)

	def get_time_budget(self) -> int:
		"""Get the owner's available minutes per day."""
		return self.available_minutes_per_day

	def add_pet(self, pet: Pet) -> None:
		"""Add a pet to the owner's collection."""
		pet.owner_id = self.owner_id
		for task in pet.tasks:
			task.owner_id = self.owner_id
			task.pet_id = pet.pet_id
		self.pets.append(pet)

	def remove_pet(self, pet_id: str) -> bool:
		"""Remove a pet from the owner's collection; return True if found and removed."""
		for idx, pet in enumerate(self.pets):
			if pet.pet_id == pet_id:
				self.pets.pop(idx)
				return True
		return False

	def get_all_tasks(self) -> list[Task]:
		"""Get all tasks from all owner's pets."""
		all_tasks: list[Task] = []
		for pet in self.pets:
			all_tasks.extend(pet.tasks)
		return all_tasks

	def to_dict(self) -> dict[str, Any]:
		return {
			"owner_id": self.owner_id,
			"name": self.name,
			"available_minutes_per_day": self.available_minutes_per_day,
			"preferred_start_time": _time_to_str(self.preferred_start_time),
			"preferred_end_time": _time_to_str(self.preferred_end_time),
			"notes": self.notes,
			"pets": [pet.to_dict() for pet in self.pets],
		}

	def save_to_json(self, file_path: str = "data.json") -> None:
		"""Persist owner, pets, and tasks to a JSON file."""
		path = Path(file_path)
		path.parent.mkdir(parents=True, exist_ok=True)
		path.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")

	@classmethod
	def from_dict(cls, data: dict[str, Any]) -> Owner:
		available_minutes = int(data["available_minutes_per_day"])
		preferred_start = _parse_time(data["preferred_start_time"])
		preferred_end = _parse_time(data["preferred_end_time"])

		_validate_positive_duration(available_minutes, "available_minutes_per_day")
		_validate_time_range(preferred_start, preferred_end, "preferred_start_time", "preferred_end_time")

		pets = [Pet.from_dict(pet_data) for pet_data in data.get("pets", [])]
		owner_id = data.get("owner_id", str(uuid4()))

		for pet in pets:
			pet.owner_id = owner_id
			for task in pet.tasks:
				task.owner_id = owner_id
				task.pet_id = pet.pet_id

		return cls(
			name=data["name"],
			available_minutes_per_day=available_minutes,
			preferred_start_time=preferred_start,
			preferred_end_time=preferred_end,
			notes=data.get("notes", ""),
			owner_id=owner_id,
			pets=pets,
		)

	@classmethod
	def load_from_json(cls, file_path: str = "data.json") -> Owner | None:
		"""Load owner state from a JSON file; return None if missing or empty."""
		path = Path(file_path)
		if not path.exists() or path.stat().st_size == 0:
			return None

		data = json.loads(path.read_text(encoding="utf-8"))
		return cls.from_dict(data)


@dataclass
class Pet:
	name: str
	species: str
	breed: str
	age_years: float
	weight_kg: float
	health_notes: str = ""
	pet_id: str = field(default_factory=lambda: str(uuid4()))
	owner_id: str = ""
	tasks: list[Task] = field(default_factory=list)

	def get_profile_summary(self) -> str:
		"""Get a formatted profile summary of the pet."""
		return (
			f"{self.name} is a {self.age_years:.1f}-year-old {self.breed} "
			f"{self.species} weighing {self.weight_kg:.1f} kg."
		)

	def to_dict(self) -> dict[str, Any]:
		return {
			"pet_id": self.pet_id,
			"owner_id": self.owner_id,
			"name": self.name,
			"species": self.species,
			"breed": self.breed,
			"age_years": self.age_years,
			"weight_kg": self.weight_kg,
			"health_notes": self.health_notes,
			"tasks": [task.to_dict() for task in self.tasks],
		}

	def add_task(self, task: Task) -> None:
		"""Add a task to the pet; assign ownership IDs."""
		task.pet_id = self.pet_id
		task.owner_id = self.owner_id
		self.tasks.append(task)

	def remove_task(self, task_id: str) -> bool:
		"""Remove a task from the pet; return True if found and removed."""
		for idx, task in enumerate(self.tasks):
			if task.task_id == task_id:
				self.tasks.pop(idx)
				return True
		return False

	def get_tasks_due_on(self, target_date: date) -> list[Task]:
		"""Get all tasks for the pet that are due on a specific date."""
		return [task for task in self.tasks if task.is_due_on(target_date)]

	@classmethod
	def from_dict(cls, data: dict[str, Any]) -> Pet:
		age = float(data["age_years"])
		weight = float(data["weight_kg"])

		_validate_positive_float(age, "age_years")
		_validate_positive_float(weight, "weight_kg")

		tasks = [Task.from_dict(task_data) for task_data in data.get("tasks", [])]
		pet_id = data.get("pet_id", str(uuid4()))
		owner_id = data.get("owner_id", "")

		for task in tasks:
			task.pet_id = pet_id
			if owner_id:
				task.owner_id = owner_id

		return cls(
			name=data["name"],
			species=data["species"],
			breed=data["breed"],
			age_years=age,
			weight_kg=weight,
			health_notes=data.get("health_notes", ""),
			pet_id=pet_id,
			owner_id=owner_id,
			tasks=tasks,
		)


@dataclass
class Task:
	name: str
	category: TaskCategory
	duration_minutes: int
	priority: Priority
	is_recurring: bool
	recurrence_days: list[str] = field(default_factory=list)
	preferred_time_window: tuple[time, time] | None = None
	preferred_time: time | None = None
	frequency: str = "once"
	is_completed: bool = False
	completed_on: date | None = None
	scheduled_for: date | None = None
	notes: str = ""
	task_id: str = field(default_factory=lambda: str(uuid4()))
	owner_id: str = field(default_factory=lambda: str(uuid4()))
	pet_id: str = field(default_factory=lambda: str(uuid4()))

	def is_schedulable_at(self, t: time) -> bool:
		"""Check if task can be scheduled at the given time."""
		if self.preferred_time is not None and t != self.preferred_time:
			return False
		if self.preferred_time_window is None:
			return True
		start, end = self.preferred_time_window
		return start <= t <= end

	def mark_completed(self, completed_date: date | None = None) -> None:
		"""Mark task as complete with optional completion date."""
		self.is_completed = True
		self.completed_on = completed_date or date.today()

	def mark_complete(self, completed_date: date | None = None) -> None:
		"""Compatibility alias for mark_completed()."""
		self.mark_completed(completed_date)

	def get_next_occurrence_date(self, from_date: date | None = None) -> date | None:
		"""Return the next due date for a recurring task.

		Uses `timedelta` to compute the next date from `from_date` (or today).
		- daily: next day
		- weekly with recurrence_days: next listed weekday strictly after base date
		- weekly without recurrence_days: seven days later

		Returns None for non-recurring/unsupported frequencies.
		"""
		base_date = from_date or date.today()

		if self.frequency == "daily":
			return base_date + timedelta(days=1)

		if self.frequency == "weekly":
			if self.recurrence_days:
				weekday_to_index = {
					"Monday": 0,
					"Tuesday": 1,
					"Wednesday": 2,
					"Thursday": 3,
					"Friday": 4,
					"Saturday": 5,
					"Sunday": 6,
				}
				recurrence_indexes = [
					weekday_to_index[day]
					for day in self.recurrence_days
					if day in weekday_to_index
				]
				if recurrence_indexes:
					days_until_candidates = [
						((target_idx - base_date.weekday()) % 7) or 7
						for target_idx in recurrence_indexes
					]
					return base_date + timedelta(days=min(days_until_candidates))
			return base_date + timedelta(days=7)

		return None

	def create_next_occurrence(self, completed_date: date | None = None) -> Task | None:
		"""Create the next Task instance for recurring rollover.

		The returned task copies scheduling metadata (priority, preferred times,
		recurrence) and sets:
		- is_completed = False
		- completed_on = None
		- scheduled_for = computed next date

		Returns None when no next occurrence can be computed.
		"""
		next_date = self.get_next_occurrence_date(completed_date)
		if next_date is None:
			return None

		return Task(
			name=self.name,
			category=self.category,
			duration_minutes=self.duration_minutes,
			priority=self.priority,
			is_recurring=self.is_recurring,
			recurrence_days=list(self.recurrence_days),
			preferred_time_window=self.preferred_time_window,
			preferred_time=self.preferred_time,
			frequency=self.frequency,
			is_completed=False,
			completed_on=None,
			scheduled_for=next_date,
			notes=self.notes,
			owner_id=self.owner_id,
			pet_id=self.pet_id,
		)

	def mark_pending(self) -> None:
		"""Mark task as not completed."""
		self.is_completed = False
		self.completed_on = None

	def is_due_on(self, target_date: date) -> bool:
		"""Check if task is due on a specific date based on frequency and recurrence."""
		if self.scheduled_for is not None:
			return target_date == self.scheduled_for and not self.is_completed

		if self.frequency == "once":
			return not self.is_completed
		if self.frequency == "daily":
			return True
		if self.frequency == "weekly":
			if not self.recurrence_days:
				return True
			return target_date.strftime("%A") in self.recurrence_days
		return True

	def to_dict(self) -> dict[str, Any]:
		return {
			"task_id": self.task_id,
			"name": self.name,
			"category": self.category.value,
			"duration_minutes": self.duration_minutes,
			"priority": self.priority.name,
			"is_recurring": self.is_recurring,
			"recurrence_days": self.recurrence_days,
			"preferred_time": None if self.preferred_time is None else _time_to_str(self.preferred_time),
			"preferred_time_window": None
			if self.preferred_time_window is None
			else [
				_time_to_str(self.preferred_time_window[0]),
				_time_to_str(self.preferred_time_window[1]),
			],
			"frequency": self.frequency,
			"is_completed": self.is_completed,
			"completed_on": None if self.completed_on is None else _date_to_str(self.completed_on),
			"scheduled_for": None if self.scheduled_for is None else _date_to_str(self.scheduled_for),
			"notes": self.notes,
			"owner_id": self.owner_id,
			"pet_id": self.pet_id,
		}

	@classmethod
	def from_dict(cls, data: dict[str, Any]) -> Task:
		duration = int(data["duration_minutes"])
		_validate_positive_duration(duration, "duration_minutes")

		preferred_time_data = data.get("preferred_time")
		preferred_time = None if preferred_time_data is None else _parse_time(preferred_time_data)

		preferred_time_window_data = data.get("preferred_time_window")
		preferred_time_window: tuple[time, time] | None = None
		if preferred_time_window_data:
			start_time = _parse_time(preferred_time_window_data[0])
			end_time = _parse_time(preferred_time_window_data[1])
			_validate_time_range(start_time, end_time, "preferred_time_window[0]", "preferred_time_window[1]")
			preferred_time_window = (start_time, end_time)

		frequency = str(data.get("frequency", "weekly" if _parse_bool(data.get("is_recurring", False)) else "once"))
		if frequency not in {"once", "daily", "weekly"}:
			raise ValidationError(f"frequency must be one of once/daily/weekly, got {frequency}")

		completed_on_data = data.get("completed_on")
		completed_on = None if completed_on_data is None else _parse_date(completed_on_data)
		is_completed = _parse_bool(data.get("is_completed", False))
		scheduled_for_data = data.get("scheduled_for")
		scheduled_for = None if scheduled_for_data is None else _parse_date(scheduled_for_data)

		return cls(
			task_id=data.get("task_id", str(uuid4())),
			name=data["name"],
			category=TaskCategory(data["category"]),
			duration_minutes=duration,
			priority=Priority[data["priority"]],
			is_recurring=_parse_bool(data["is_recurring"]),
			recurrence_days=list(data.get("recurrence_days", [])),
			preferred_time_window=preferred_time_window,
			preferred_time=preferred_time,
			frequency=frequency,
			is_completed=is_completed,
			completed_on=completed_on,
			scheduled_for=scheduled_for,
			notes=data.get("notes", ""),
			owner_id=data.get("owner_id", str(uuid4())),
			pet_id=data.get("pet_id", str(uuid4())),
		)


@dataclass
class ScheduledTask:
	task: Task
	start_time: time
	reasoning: str
	end_time: time = field(init=False)

	def __post_init__(self) -> None:
		self.end_time = _add_minutes_to_time(self.start_time, self.task.duration_minutes)

	def overlaps_with(self, other: ScheduledTask) -> bool:
		"""Check if this scheduled task overlaps with another."""
		return self.start_time < other.end_time and other.start_time < self.end_time

	def duration(self) -> int:
		"""Get the duration of the task in minutes."""
		return self.task.duration_minutes


@dataclass
class DailyPlan:
	date: date
	scheduled_tasks: list[ScheduledTask] = field(default_factory=list)
	unscheduled_tasks: list[Task] = field(default_factory=list)
	total_minutes_scheduled: int = 0
	warnings: list[str] = field(default_factory=list)
	owner_id: str = ""
	pet_id: str = ""

	def add_scheduled_task(self, st: ScheduledTask) -> None:
		"""Add a scheduled task to the plan, maintaining time order."""
		self.scheduled_tasks.append(st)
		self.scheduled_tasks.sort(key=lambda item: item.start_time)
		self.total_minutes_scheduled += st.duration()

	def get_summary(self) -> str:
		"""Get a summary of scheduled and unscheduled tasks."""
		return (
			f"Scheduled {len(self.scheduled_tasks)} task(s) totaling "
			f"{self.total_minutes_scheduled} minutes. "
			f"{len(self.unscheduled_tasks)} task(s) remain unscheduled."
		)

	def has_conflicts(self) -> bool:
		"""Check if any scheduled tasks overlap (O(n²) naive approach)."""
		for i, task_i in enumerate(self.scheduled_tasks):
			for task_j in self.scheduled_tasks[i + 1 :]:
				if task_i.overlaps_with(task_j):
					return True
		return False

	def find_conflicts_sorted(self) -> list[tuple[ScheduledTask, ScheduledTask]]:
		"""Find conflicting task pairs using sweep-line algorithm (O(n log n))."""
		if len(self.scheduled_tasks) <= 1:
			return []
		
		# Create events: (time, is_start, task)
		events = []
		for st in self.scheduled_tasks:
			events.append((st.start_time, True, st))
			events.append((st.end_time, False, st))
		
		# Sort by time, with ends before starts at same time
		events.sort(key=lambda e: (e[0], not e[1]))
		
		conflicts = []
		active_tasks = []
		
		for time_val, is_start, task in events:
			if is_start:
				# Check conflicts with all active tasks
				for active_task in active_tasks:
					if task.overlaps_with(active_task):
						conflicts.append((active_task, task))
				active_tasks.append(task)
			else:
				if task in active_tasks:
					active_tasks.remove(task)
		
		return conflicts

	def to_display_df(self) -> pd.DataFrame:
		"""Convert scheduled tasks to a pandas DataFrame for clean display."""
		rows = [
			{
				"Task": st.task.name,
				"Category": st.task.category.value,
				"Priority": st.task.priority.name,
				"Start": st.start_time.strftime("%H:%M"),
				"End": st.end_time.strftime("%H:%M"),
				"Duration (min)": st.duration(),
				"Reasoning": st.reasoning,
			}
			for st in self.scheduled_tasks
		]
		return pd.DataFrame(rows)


@dataclass
class Scheduler:
	owner: Owner
	pet: Pet | None = None
	tasks: list[Task] = field(default_factory=list)

	def generate_plan(self, target_date: date) -> DailyPlan:
		"""Main scheduler entry point for generating one-day plans."""
		plan = DailyPlan(
			date=target_date,
			owner_id=self.owner.owner_id,
			pet_id=self.pet.pet_id if self.pet is not None else "multi-pet",
		)

		all_tasks = self._retrieve_owner_pet_tasks(target_date)
		sorted_tasks = self._sort_tasks_by_priority(all_tasks)

		for task in sorted_tasks:
			if plan.total_minutes_scheduled + task.duration_minutes > self.owner.available_minutes_per_day:
				plan.unscheduled_tasks.append(task)
				continue

			next_slot = self._find_next_available_slot(plan, task)
			if next_slot is None:
				plan.unscheduled_tasks.append(task)
				continue

			scheduled_task = ScheduledTask(
				task=task,
				start_time=next_slot,
				reasoning=self._explain_placement(task, next_slot),
			)
			plan.add_scheduled_task(scheduled_task)

		plan.warnings.extend(self._handle_overflow(plan.unscheduled_tasks))
		plan.warnings.extend(self._detect_lightweight_conflicts(all_tasks, plan))
		return plan

	def mark_task_completed(self, task_id: str, completed_date: date | None = None) -> Task | None:
		"""Mark a task complete and auto-create next instance for daily/weekly tasks."""
		for pet in self.owner.pets:
			for task in pet.tasks:
				if task.task_id != task_id:
					continue

				effective_completed_date = completed_date or date.today()
				task.mark_completed(effective_completed_date)

				if task.frequency not in {"daily", "weekly"}:
					return None

				next_task = task.create_next_occurrence(effective_completed_date)
				if next_task is not None:
					pet.add_task(next_task)
				return next_task

		return None

	# ========================================================================
	# PUBLIC CONVENIENCE METHODS FOR FILTERING & SORTING
	# ========================================================================

	def get_tasks_for_pet(self, pet_id: str) -> list[Task]:
		"""Get all tasks for a specific pet (regardless of completion status)."""
		return [task for task in self.owner.get_all_tasks() if task.pet_id == pet_id]

	def get_pending_tasks(self, target_date: date | None = None) -> list[Task]:
		"""Get all non-completed tasks due on target date (or today if not specified)."""
		if target_date is None:
			target_date = date.today()
		return [
			task
			for task in self.owner.get_all_tasks()
			if not task.is_completed and task.is_due_on(target_date)
		]

	def get_recurring_tasks(self) -> list[Task]:
		"""Get all recurring tasks across all pets."""
		return [task for task in self.owner.get_all_tasks() if task.is_recurring]

	def get_tasks_by_category(self, category: TaskCategory) -> list[Task]:
		"""Get all tasks of a specific category."""
		return [task for task in self.owner.get_all_tasks() if task.category == category]

	def get_high_priority_tasks(self, target_date: date | None = None) -> list[Task]:
		"""Get all high-priority tasks due on target date."""
		if target_date is None:
			target_date = date.today()
		return [
			task
			for task in self.get_pending_tasks(target_date)
			if task.priority == Priority.HIGH
		]

	def sort_by_priority_then_time(self, tasks: list[Task] | None = None) -> list[dict[str, Any]]:
		"""Return tasks sorted by priority first, then preferred time.

		Ordering:
		- Priority: HIGH -> MEDIUM -> LOW
		- Preferred time: earlier first
		- Name: case-insensitive fallback for stable display
		"""
		tasks_to_sort = self.owner.get_all_tasks() if tasks is None else tasks
		sorted_tasks = self._sort_tasks_by_priority(tasks_to_sort)

		return [
			{
				"task_id": task.task_id,
				"name": task.name,
				"time": task.preferred_time.strftime("%H:%M") if task.preferred_time is not None else "Unscheduled",
				"priority": task.priority.name,
				"is_completed": task.is_completed,
				"pet_id": task.pet_id,
			}
			for task in sorted_tasks
		]

	def sort_by_time(self, tasks: list[Task] | None = None) -> list[dict[str, Any]]:
		"""Return tasks sorted by preferred time with HH:MM formatting.

		Tasks without a preferred_time are placed at the end and labeled as "Unscheduled".
		"""
		tasks_to_sort = self.owner.get_all_tasks() if tasks is None else tasks
		sorted_tasks = sorted(
			tasks_to_sort,
			key=lambda task: (task.preferred_time is None, task.preferred_time or time(23, 59), task.name.lower()),
		)

		return [
			{
				"task_id": task.task_id,
				"name": task.name,
				"time": task.preferred_time.strftime("%H:%M") if task.preferred_time is not None else "Unscheduled",
				"priority": task.priority.name,
				"is_completed": task.is_completed,
				"pet_id": task.pet_id,
			}
			for task in sorted_tasks
		]

	def filter_tasks(
		self,
		is_completed: bool | None = None,
		name: str | None = None,
		pet_name: str | None = None,
		tasks: list[Task] | None = None,
	) -> list[Task]:
		"""Filter tasks by completion status, task name, and/or pet name.

		- is_completed: True/False to filter by status, None to ignore status.
		- name: case-insensitive substring match on task name.
		- pet_name: case-insensitive substring match on associated pet name.
		"""
		filtered = list(self.owner.get_all_tasks() if tasks is None else tasks)
		pet_name_by_id = {pet.pet_id: pet.name for pet in self.owner.pets}

		if is_completed is not None:
			filtered = [task for task in filtered if task.is_completed == is_completed]

		if name is not None and name.strip():
			needle = name.strip().lower()
			filtered = [task for task in filtered if needle in task.name.lower()]

		if pet_name is not None and pet_name.strip():
			pet_needle = pet_name.strip().lower()
			filtered = [
				task
				for task in filtered
				if pet_needle in pet_name_by_id.get(task.pet_id, "").lower()
			]

		return filtered

	def _retrieve_owner_pet_tasks(self, target_date: date) -> list[Task]:
		"""Retrieve relevant tasks from owner's pets, filtered by date and completion status."""
		owner_tasks = self.owner.get_all_tasks()

		if self.tasks:
			extra_tasks = [task for task in self.tasks if task not in owner_tasks]
			owner_tasks.extend(extra_tasks)

		if self.pet is not None:
			owner_tasks = [task for task in owner_tasks if task.pet_id == self.pet.pet_id]

		valid_pet_ids = {pet.pet_id for pet in self.owner.pets}
		owner_tasks = [
			task
			for task in owner_tasks
			if task.owner_id == self.owner.owner_id and task.pet_id in valid_pet_ids
		]

		return [task for task in owner_tasks if task.is_due_on(target_date) and not task.is_completed]

	def _sort_tasks_by_priority(self, tasks: list[Task]) -> list[Task]:
		"""Sort tasks by priority (HIGH → MEDIUM → LOW), then by preferred time and duration."""
		return sorted(
			tasks,
			key=lambda task: (
				-task.priority.value,
				task.preferred_time or time(23, 59),
				task.duration_minutes,
			),
		)

	def _find_next_available_slot(self, plan: DailyPlan, task: Task) -> time | None:
		"""Find the earliest valid slot for a task using a linear gap scan.

		Algorithm:
		1. Resolve an effective time window from owner + task constraints.
		2. If task has strict preferred_time, validate only that candidate.
		3. Otherwise scan gaps between already scheduled tasks in order and place
		   at the earliest feasible start.

		This favors readability and predictable behavior while reducing repeated
		overlap checks from candidate-based probing.
		"""
		effective_window = self._resolve_effective_window(task)
		if effective_window is None:
			return None
		window_start, window_end = effective_window

		# If a strict preferred_time exists, validate only that single candidate.
		if task.preferred_time is not None:
			candidate = task.preferred_time
			if candidate < window_start or candidate > window_end:
				return None
			if not _slot_end_within_bounds(candidate, task.duration_minutes, window_end):
				return None
			if not self._check_time_window_preference(task, candidate):
				return None
			if not self._is_candidate_non_overlapping(plan, task, candidate):
				return None
			return candidate

		# Otherwise, scan gaps from earliest feasible time to the end of window.
		current_start = window_start
		for existing in plan.scheduled_tasks:
			# Ignore tasks fully before our current pointer.
			if existing.end_time <= current_start:
				continue

			# No more useful gaps once we pass scheduling window.
			if existing.start_time >= window_end:
				break

			# Try placing into the gap before this existing task.
			if self._can_fit_in_gap(current_start, existing.start_time, task, window_end):
				if self._check_time_window_preference(task, current_start):
					return current_start

			# Move pointer to the end of the blocking task.
			if existing.end_time > current_start:
				current_start = existing.end_time

		# Try tail gap from last pointer to window end.
		if self._can_fit_in_gap(current_start, window_end, task, window_end):
			if self._check_time_window_preference(task, current_start):
				return current_start

		return None

	def _resolve_effective_window(self, task: Task) -> tuple[time, time] | None:
		"""Merge owner and task windows into one schedulable interval.

		Returns:
		- (window_start, window_end) when constraints overlap.
		- None when there is no valid overlap.
		"""
		window_start = self.owner.preferred_start_time
		window_end = self.owner.preferred_end_time

		if task.preferred_time_window is not None:
			task_window_start, task_window_end = task.preferred_time_window
			window_start = max(window_start, task_window_start)
			window_end = min(window_end, task_window_end)

		if window_start >= window_end:
			return None
		return (window_start, window_end)

	def _can_fit_in_gap(self, start: time, gap_end: time, task: Task, window_end: time) -> bool:
		"""Check whether task duration fits inside a candidate gap.

		A task fits if its end time is within both:
		- the current gap boundary (`gap_end`)
		- the overall effective scheduling boundary (`window_end`)
		"""
		effective_bound = min(gap_end, window_end)
		return _slot_end_within_bounds(start, task.duration_minutes, effective_bound)

	def _is_candidate_non_overlapping(self, plan: DailyPlan, task: Task, candidate: time) -> bool:
		"""Return True if candidate interval does not overlap existing schedule.

		Uses direct interval intersection checks against each scheduled task:
		[candidate_start, candidate_end) intersects [existing_start, existing_end)
		when start < other_end and other_start < end.
		"""
		candidate_start = datetime.combine(date.today(), candidate)
		candidate_end = candidate_start + timedelta(minutes=task.duration_minutes)

		for existing in plan.scheduled_tasks:
			existing_start = datetime.combine(date.today(), existing.start_time)
			existing_end = datetime.combine(date.today(), existing.end_time)
			if candidate_start < existing_end and existing_start < candidate_end:
				return False
		return True

	def _check_time_window_preference(self, task: Task, proposed_time: time) -> bool:
		"""Validate that proposed time meets both task's and owner's time constraints."""
		if not task.is_schedulable_at(proposed_time):
			return False

		try:
			_validate_owner_time_window(
				proposed_time,
				self.owner.preferred_start_time,
				self.owner.preferred_end_time,
				task_name=task.name,
			)
		except TimeConstraintError:
			return False

		return True

	def _explain_placement(self, task: Task, proposed_time: time) -> str:
		"""Generate human-readable explanation for why task was placed at given time."""
		priority_reason = f"priority {task.priority.name}"
		window_reason = "within task window" if task.preferred_time_window else "within owner window"
		return (
			f"Scheduled {task.name} at {proposed_time.strftime('%H:%M')} based on {priority_reason} "
			f"and first available slot {window_reason}."
		)

	def _handle_overflow(self, unfit_tasks: list[Task]) -> list[str]:
		"""Build warning messages for tasks that could not be scheduled."""
		warnings: list[str] = []
		for task in unfit_tasks:
			warnings.append(
				f"Unable to schedule '{task.name}' for pet_id={task.pet_id}; "
				f"insufficient time window or budget."
			)
		return warnings

	def _detect_lightweight_conflicts(self, tasks: list[Task], plan: DailyPlan) -> list[str]:
		"""Return non-fatal warnings for timing conflicts.

		Lightweight strategy:
		- Requested-time conflicts: multiple tasks asking for the same HH:MM slot.
		- Scheduled overlaps: defensive pass over final schedule conflict pairs.

		This method never raises and is intended for user-facing warnings so plan
		generation can complete even when conflicts exist.
		"""
		warnings: list[str] = []
		pet_name_by_id = {pet.pet_id: pet.name for pet in self.owner.pets}

		# 1) Requested-time collisions before scheduling (same HH:MM across tasks).
		requested_by_time: dict[time, list[Task]] = {}
		for task in tasks:
			if task.preferred_time is None:
				continue
			requested_by_time.setdefault(task.preferred_time, []).append(task)

		for conflict_time, grouped_tasks in requested_by_time.items():
			if len(grouped_tasks) < 2:
				continue
			participants = ", ".join(
				f"{task.name} ({pet_name_by_id.get(task.pet_id, 'Unknown Pet')})"
				for task in grouped_tasks
			)
			warnings.append(
				f"Timing conflict request at {conflict_time.strftime('%H:%M')}: {participants}. "
				"Scheduler will keep running and place tasks in next available slots."
			)

		# 2) Defensive check for overlaps in produced schedule.
		for first, second in plan.find_conflicts_sorted():
			first_pet = pet_name_by_id.get(first.task.pet_id, "Unknown Pet")
			second_pet = pet_name_by_id.get(second.task.pet_id, "Unknown Pet")
			warnings.append(
				"Scheduled overlap detected: "
				f"{first.task.name} ({first_pet}) and {second.task.name} ({second_pet}) overlap."
			)

		return warnings
