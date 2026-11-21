
from collections import defaultdict
from ortools.sat.python import cp_model


def find_cycle(tasks):
    by_id = {t["id"]: t for t in tasks}
    visited = set()
    path = []

    def check(task_id):
        if task_id in path:
            return path[path.index(task_id):]
        if task_id in visited:
            return []

        path.append(task_id)
        for dep in by_id[task_id]["depends_on"]:
            cycle = check(dep)
            if cycle:
                return cycle

        path.pop()
        visited.add(task_id)
        return []

    for task in tasks:
        cycle = check(task["id"])
        if cycle:
            return cycle
    return []


def schedule(tasks, deadline_day):
    cycle = find_cycle(tasks)

    if cycle:
        return {
            "status": "cycle",
            "schedule": [],
            "end_day": None,
            "deadline_day": deadline_day,
            "meets_deadline": None,
            "days_late": None,
            "cycle": cycle,
        }

    if not tasks:
        return {
            "status": "scheduled",
            "schedule": [],
            "end_day": 0,
            "deadline_day": deadline_day,
            "meets_deadline": 0 <= deadline_day,
            "days_late": max(0, -deadline_day),
            "cycle": [],
        }

    model = cp_model.CpModel()
    horizon = sum(t["duration_days"] for t in tasks)

    starts = {}
    ends = {}
    owners = defaultdict(list)

    # Set up the time variables for each task
    for t in tasks:
        task_id = t["id"]
        duration = t["duration_days"]

        start = model.NewIntVar(0, horizon, f"start_{task_id}")
        end = model.NewIntVar(0, horizon, f"end_{task_id}")
        interval = model.NewIntervalVar(start, duration, end, f"task_{task_id}")

        starts[task_id] = start
        ends[task_id] = end

        if t["owner"] is not None:
            owners[t["owner"]].append(interval)

    # A task starts after its dependencies finish
    for t in tasks:
        for dep in t["depends_on"]:
            model.Add(starts[t["id"]] >= ends[dep])

    # One person cannot work on two tasks at once
    for intervals in owners.values():
        model.AddNoOverlap(intervals)

    # Find the earliest possible finish
    end_var = model.NewIntVar(0, horizon, "end_day")
    model.AddMaxEquality(end_var, list(ends.values()))
    model.Minimize(end_var)

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 7
    result = solver.Solve(model)

    if result not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        raise RuntimeError("Could not find a valid schedule")

    items = []
    for t in tasks:
        task_id = t["id"]
        items.append({
            "id": task_id,
            "start_day": solver.Value(starts[task_id]),
            "end_day": solver.Value(ends[task_id]),
        })

    end_day = max(i["end_day"] for i in items)

    return {
        "status": "scheduled",
        "schedule": items,
        "end_day": end_day,
        "deadline_day": deadline_day,
        "meets_deadline": end_day <= deadline_day if deadline_day is not None else None,
        "days_late": max(0, end_day - deadline_day) if deadline_day is not None else None,
        "cycle": [],
        "optimization_status": solver.StatusName(result),
    }
