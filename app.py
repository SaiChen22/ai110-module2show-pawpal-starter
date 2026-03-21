from datetime import date, time

import streamlit as st

from pawpal_system import Owner, Pet, Priority, Scheduler, Task, TaskCategory

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="wide")

st.title("🐾 PawPal+")

st.markdown(
    """
Welcome to the PawPal+ starter app.

This file is intentionally thin. It gives you a working Streamlit app so you can start quickly,
but **it does not implement the project logic**. Your job is to design the system and build it.

Use this app as your interactive demo once your backend classes/functions exist.
"""
)

with st.expander("Scenario", expanded=True):
    st.markdown(
        """
**PawPal+** is a pet care planning assistant. It helps a pet owner plan care tasks
for their pet(s) based on constraints like time, priority, and preferences.

You will design and implement the scheduling logic and connect it to this Streamlit UI.
"""
    )

with st.expander("What you need to build", expanded=True):
    st.markdown(
        """
At minimum, your system should:
- Represent pet care tasks (what needs to happen, how long it takes, priority)
- Represent the pet and the owner (basic info and preferences)
- Build a plan/schedule for a day that chooses and orders tasks based on constraints
- Explain the plan (why each task was chosen and when it happens)
"""
    )

st.divider()

# Initialize session state with Owner, Pet, and Scheduler
if "owner" not in st.session_state:
    st.session_state.owner = Owner(
        name="Jordan",
        available_minutes_per_day=120,
        preferred_start_time=time(7, 0),
        preferred_end_time=time(20, 0),
    )
    st.session_state.pet = Pet(name="Mochi", species="dog", breed="Corgi Mix", age_years=4.0, weight_kg=11.5)
    st.session_state.owner.add_pet(st.session_state.pet)
    st.session_state.scheduler = Scheduler(owner=st.session_state.owner)

st.subheader("Owner & Pet Setup")
owner = st.session_state.owner
pet = st.session_state.pet

col1, col2 = st.columns(2)
with col1:
    new_owner_name = st.text_input("Owner name", value=owner.name)
    if new_owner_name != owner.name:
        owner.name = new_owner_name
        st.session_state.owner = owner

with col2:
    new_pet_name = st.text_input("Pet name", value=pet.name)
    if new_pet_name != pet.name:
        pet.name = new_pet_name
        st.session_state.pet = pet

st.info(f"📋 {owner.name} has {len(owner.pets)} pet(s). {pet.name} has {len(pet.tasks)} task(s).")

st.markdown("### Add a Task")
st.caption("Create tasks for your pet to be scheduled.")

col1, col2, col3, col4 = st.columns(4)
with col1:
    task_name = st.text_input("Task name", value="Morning Walk")
with col2:
    duration = st.number_input("Duration (min)", min_value=1, max_value=240, value=30)
with col3:
    category = st.selectbox("Category", ["walk", "feed", "medication", "grooming", "enrichment", "vet"])
with col4:
    priority = st.selectbox("Priority", ["high", "medium", "low"], index=0)

col_time1, col_time2, col_add = st.columns(3)
with col_time1:
    pref_hour = st.number_input("Preferred hour (0-23)", min_value=0, max_value=23, value=8)
with col_time2:
    pref_min = st.number_input("Preferred minute (0-59)", min_value=0, max_value=59, value=0)
with col_add:
    st.write("")
    if st.button("➕ Add Task"):
        category_map = {
            "walk": TaskCategory.WALK,
            "feed": TaskCategory.FEED,
            "medication": TaskCategory.MEDICATION,
            "grooming": TaskCategory.GROOMING,
            "enrichment": TaskCategory.ENRICHMENT,
            "vet": TaskCategory.VET,
        }
        priority_map = {"high": Priority.HIGH, "medium": Priority.MEDIUM, "low": Priority.LOW}
        
        new_task = Task(
            name=task_name,
            category=category_map[category],
            duration_minutes=int(duration),
            priority=priority_map[priority],
            is_recurring=True,
            frequency="daily",
            preferred_time=time(int(pref_hour), int(pref_min)),
        )
        pet.add_task(new_task)
        st.session_state.pet = pet
        st.success(f"✅ Added task '{task_name}' to {pet.name}")
        st.rerun()

if pet.tasks:
    st.write(f"### Tasks for {pet.name}")

    scheduler = st.session_state.scheduler

    filter_col1, filter_col2 = st.columns(2)
    with filter_col1:
        status_filter = st.selectbox("Filter by status", ["All", "Pending", "Completed"], index=0)
    with filter_col2:
        name_filter = st.text_input("Filter by task name", value="", placeholder="e.g., walk")

    is_completed_filter = None
    if status_filter == "Pending":
        is_completed_filter = False
    elif status_filter == "Completed":
        is_completed_filter = True

    filtered_tasks = scheduler.filter_tasks(
        is_completed=is_completed_filter,
        name=name_filter,
        tasks=pet.tasks,
    )
    sorted_tasks = scheduler.sort_by_time(filtered_tasks)

    task_display = [
        {
            "Task": item["name"],
            "Time": item["time"],
            "Priority": item["priority"],
            "Status": "Completed" if item["is_completed"] else "Pending",
        }
        for item in sorted_tasks
    ]

    st.success(f"Showing {len(task_display)} sorted task(s) for {pet.name}.")
    st.table(task_display)
else:
    st.info(f"No tasks yet for {pet.name}. Add one above!")

st.divider()

st.subheader("📅 Generate Daily Schedule")
st.caption("Create an optimized schedule based on priority, time windows, and availability.")

if st.button("🔄 Generate Schedule for Today", use_container_width=True):
    scheduler = st.session_state.scheduler
    plan = scheduler.generate_plan(date.today())
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Scheduled Tasks", len(plan.scheduled_tasks))
    with col2:
        st.metric("Total Minutes", plan.total_minutes_scheduled)
    with col3:
        st.metric("Unscheduled", len(plan.unscheduled_tasks))
    
    if plan.scheduled_tasks:
        st.success("Schedule generated successfully.")
        st.write("### 📋 Today's Schedule")
        schedule_data = []
        for st_item in plan.scheduled_tasks:
            pet_name = next(
                (p.name for p in scheduler.owner.pets if p.pet_id == st_item.task.pet_id),
                "Unknown",
            )
            schedule_data.append({
                "Time": f"{st_item.start_time.strftime('%H:%M')}-{st_item.end_time.strftime('%H:%M')}",
                "Task": st_item.task.name,
                "Pet": pet_name,
                "Category": st_item.task.category.value,
                "Priority": st_item.task.priority.name,
                "Duration": st_item.task.duration_minutes,
                "Reasoning": st_item.reasoning,
            })
        st.table(schedule_data)
    
    if plan.unscheduled_tasks:
        st.warning(f"⚠️ {len(plan.unscheduled_tasks)} task(s) could not be scheduled")
        unscheduled_data = [
            {
                "Task": t.name,
                "Category": t.category.value,
                "Priority": t.priority.name,
                "Duration (min)": t.duration_minutes,
            }
            for t in plan.unscheduled_tasks
        ]
        st.table(unscheduled_data)
    
    if plan.warnings:
        st.warning(f"Detected {len(plan.warnings)} schedule warning(s).")
        for warning in plan.warnings:
            st.warning(warning)
    elif plan.scheduled_tasks:
        st.success("No timing conflicts detected for today's plan.")
    
    if not plan.scheduled_tasks and not plan.unscheduled_tasks:
        st.info("No tasks to schedule.")
