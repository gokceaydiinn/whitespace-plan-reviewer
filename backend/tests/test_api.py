import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.main import app  # noqa: E402


def test_plans_are_listed():
    response = TestClient(app).get("/api/plans")
    assert response.status_code == 200
    assert {plan["id"] for plan in response.json()} == {"spring-market", "lantern-festival", "harbour-run"}



def test_negative_duration():
    client = TestClient(app)

    body = {
        "tasks": [
            {
                "id": "A",
                "name": "Book venue",
                "owner": "Ann",
                "duration_days": -2,
                "depends_on": [],
            }
        ],
        "deadline_day": 10,
    }

    response = client.post("/api/schedule", json=body)

    assert response.status_code == 422
    assert "duration_days" in str(response.json()["detail"])


def test_unknown_dependency():
    client = TestClient(app)

    body = {
        "tasks": [
            {
                "id": "A",
                "name": "Book venue",
                "owner": "Ann",
                "duration_days": 3,
                "depends_on": ["UNKNOWN"],
            }
        ],
        "deadline_day": 10,
    }

    response = client.post("/api/schedule", json=body)

    assert response.status_code == 422
    assert "unknown task" in str(response.json()["detail"])


def test_duplicate_task_ids():
    client = TestClient(app)

    body = {
        "tasks": [
            {
                "id": "A",
                "name": "Book venue",
                "owner": "Ann",
                "duration_days": 2,
                "depends_on": [],
            },
            {
                "id": "A",
                "name": "Arrange catering",
                "owner": "Bob",
                "duration_days": 3,
                "depends_on": [],
            },
        ],
        "deadline_day": 10,
    }

    response = client.post("/api/schedule", json=body)

    assert response.status_code == 422
    assert "Task IDs must be unique" in str(response.json()["detail"])
