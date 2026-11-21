import json
from pathlib import Path
from pydantic import BaseModel, Field, StrictInt, StrictStr, model_validator

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .scheduler import schedule

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
DIST = ROOT / "frontend" / "dist"

app = FastAPI()

class Task(BaseModel):
    id: StrictStr
    name: StrictStr
    owner: StrictStr | None
    duration_days: StrictInt = Field(ge=1)
    depends_on: list[StrictStr]


class ScheduleRequest(BaseModel):
    tasks: list[Task] = Field(max_length=60)
    deadline_day: StrictInt

    @model_validator(mode="after")
    def check_tasks(self):
        ids = [t.id for t in self.tasks]

        if len(ids) != len(set(ids)):
            raise ValueError("Task IDs must be unique")

        for task in self.tasks:
            for dep in task.depends_on:
                if dep not in ids:
                    raise ValueError(
                        f"Task {task.id} depends on unknown task {dep}"
                    )

        return self


@app.get("/api/plans")
def list_plans():
    plans = []
    for path in sorted((DATA / "plans").glob("*.md"), reverse=True):
        title = next((line.lstrip("# ").strip() for line in path.read_text().splitlines() if line.startswith("#")), path.stem)
        plans.append({"id": path.stem, "title": title})
    return plans


@app.get("/api/plans/{plan_id}")
def get_plan(plan_id: str):
    text = (DATA / "plans" / f"{plan_id}.md").read_text()
    review = json.loads((DATA / "reviews" / f"{plan_id}.json").read_text())
    return {
        "id": plan_id,
        "text": text,
        "review": review,
        "schedule": schedule(review["tasks"], review["deadline_day"]),
    }


@app.post("/api/schedule")
def post_schedule(body: ScheduleRequest):
    return schedule(
        [task.model_dump() for task in body.tasks],
        body.deadline_day
    )


if DIST.exists():
    app.mount("/", StaticFiles(directory=DIST, html=True))
