from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from enum import Enum
from typing import Any
from uuid import uuid4

import pandas as pd


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


def _time_to_str(value: time) -> str:
	return value.isoformat()


def _add_minutes_to_time(start: time, minutes: int) -> time:
	dt = datetime.combine(date.today(), start) + timedelta(minutes=minutes)
	return dt.time().replace(microsecond=0)


@dataclass
class Owner:
	name: str
	available_minutes_per_day: int
	preferred_start_time: time
	preferred_end_time: time
	notes: str = ""

	def get_time_budget(self) -> int:
		return self.available_minutes_per_day

	def to_dict(self) -> dict[str, Any]:
		return {
			"name": self.name,
			"available_minutes_per_day": self.available_minutes_per_day,
			"preferred_start_time": _time_to_str(self.preferred_start_time),
			"preferred_end_time": _time_to_str(self.preferred_end_time),
			"notes": self.notes,
		}

	@classmethod
	def from_dict(cls, data: dict[str, Any]) -> Owner:
		return cls(
			name=data["name"],
			available_minutes_per_day=int(data["available_minutes_per_day"]),
			preferred_start_time=_parse_time(data["preferred_start_time"]),
			preferred_end_time=_parse_time(data["preferred_end_time"]),
			notes=data.get("notes", ""),
		)


@dataclass
class Pet:
	name: str
	species: str
	breed: str
	age_years: float
	weight_kg: float
	health_notes: str = ""

	def get_profile_summary(self) -> str:
		return (
			f"{self.name} is a {self.age_years:.1f}-year-old {self.breed} "
			f"{self.species} weighing {self.weight_kg:.1f} kg."
		)

	def to_dict(self) -> dict[str, Any]:
		return {
			"name": self.name,
			"species": self.species,
			"breed": self.breed,
			"age_years": self.age_years,
			"weight_kg": self.weight_kg,
			"health_notes": self.health_notes,
		}

	@classmethod
	def from_dict(cls, data: dict[str, Any]) -> Pet:
		return cls(
			name=data["name"],
			species=data["species"],
			breed=data["breed"],
			age_years=float(data["age_years"]),
			weight_kg=float(data["weight_kg"]),
			health_notes=data.get("health_notes", ""),
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
	notes: str = ""
	task_id: str = field(default_factory=lambda: str(uuid4()))

	def is_schedulable_at(self, t: time) -> bool:
		if self.preferred_time_window is None:
			return True
		start, end = self.preferred_time_window
		return start <= t <= end

	def to_dict(self) -> dict[str, Any]:
		return {
			"task_id": self.task_id,
			"name": self.name,
			"category": self.category.value,
			"duration_minutes": self.duration_minutes,
			"priority": self.priority.name,
			"is_recurring": self.is_recurring,
			"recurrence_days": self.recurrence_days,
			"preferred_time_window": None
			if self.preferred_time_window is None
			else [
				_time_to_str(self.preferred_time_window[0]),
				_time_to_str(self.preferred_time_window[1]),
			],
			"notes": self.notes,
		}

	@classmethod
	def from_dict(cls, data: dict[str, Any]) -> Task:
		preferred_time_window_data = data.get("preferred_time_window")
		preferred_time_window: tuple[time, time] | None = None
		if preferred_time_window_data:
			preferred_time_window = (
				_parse_time(preferred_time_window_data[0]),
				_parse_time(preferred_time_window_data[1]),
			)

		return cls(
			task_id=data.get("task_id", str(uuid4())),
			name=data["name"],
			category=TaskCategory(data["category"]),
			duration_minutes=int(data["duration_minutes"]),
			priority=Priority[data["priority"]],
			is_recurring=bool(data["is_recurring"]),
			recurrence_days=list(data.get("recurrence_days", [])),
			preferred_time_window=preferred_time_window,
			notes=data.get("notes", ""),
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
		return self.start_time < other.end_time and other.start_time < self.end_time

	def duration(self) -> int:
		return self.task.duration_minutes


@dataclass
class DailyPlan:
	date: date
	scheduled_tasks: list[ScheduledTask] = field(default_factory=list)
	unscheduled_tasks: list[Task] = field(default_factory=list)
	total_minutes_scheduled: int = 0
	warnings: list[str] = field(default_factory=list)

	def add_scheduled_task(self, st: ScheduledTask) -> None:
		self.scheduled_tasks.append(st)
		self.scheduled_tasks.sort(key=lambda item: item.start_time)
		self.total_minutes_scheduled += st.duration()

	def get_summary(self) -> str:
		return (
			f"Scheduled {len(self.scheduled_tasks)} task(s) totaling "
			f"{self.total_minutes_scheduled} minutes. "
			f"{len(self.unscheduled_tasks)} task(s) remain unscheduled."
		)

	def has_conflicts(self) -> bool:
		for i, task_i in enumerate(self.scheduled_tasks):
			for task_j in self.scheduled_tasks[i + 1 :]:
				if task_i.overlaps_with(task_j):
					return True
		return False

	def to_display_df(self) -> pd.DataFrame:
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
	pet: Pet
	tasks: list[Task] = field(default_factory=list)

	def generate_plan(self, target_date: date) -> DailyPlan:
		"""Main scheduler entry point for generating one-day plans."""
		raise NotImplementedError

	def _sort_tasks_by_priority(self, tasks: list[Task]) -> list[Task]:
		"""Sort tasks by priority (HIGH -> MEDIUM -> LOW)."""
		raise NotImplementedError

	def _find_next_available_slot(self, plan: DailyPlan, task: Task) -> time | None:
		"""Greedy slot finder based on owner preferences and existing schedule."""
		raise NotImplementedError

	def _check_time_window_preference(self, task: Task, proposed_time: time) -> bool:
		"""Validate whether proposed time meets task's preferred window."""
		raise NotImplementedError

	def _explain_placement(self, task: Task, proposed_time: time) -> str:
		"""Generate human-readable scheduling rationale."""
		raise NotImplementedError

	def _handle_overflow(self, unfit_tasks: list[Task]) -> list[str]:
		"""Build warning messages for tasks that could not be scheduled."""
		raise NotImplementedError
