import pytest
from app.review import ReviewOutput, check_review_quotes


def test_valid_review():
    plan = "Ann books the hall in three days."

    review = {
        "deadline_day": 10,
        "tasks": [{
            "id": "T1",
            "name": "Book the hall",
            "owner": "Ann",
            "duration_days": 3,
            "depends_on": [],
            "quote": "Ann books the hall in three days."
        }],
        "findings": []
    }

    validated = ReviewOutput.model_validate(review)
    result = check_review_quotes(validated.model_dump(), plan)

    assert result["tasks"][0]["id"] == "T1"


def test_invalid_quote():
    plan = "Ann books the hall in three days."

    review = {
        "deadline_day": 10,
        "tasks": [{
            "id": "T1",
            "name": "Book the hall",
            "owner": "Ann",
            "duration_days": 3,
            "depends_on": [],
            "quote": "Ann books the hall in five days."
        }],
        "findings": []
    }

    validated = ReviewOutput.model_validate(review)

    with pytest.raises(ValueError, match="Invalid quote"):
        check_review_quotes(validated.model_dump(), plan)

def test_missing_required_field():
    review = {
        "deadline_day": 10,
        "tasks": [{
            "id": "T1",
            "name": "Book the hall",
            "owner": "Ann",
            "depends_on": [],
            "quote": "Ann books the hall."
        }],
        "findings": []
    }

    with pytest.raises(ValueError):
        ReviewOutput.model_validate(review)


def test_unknown_review_dependency():
    review = {
        "deadline_day": 10,
        "tasks": [{
            "id": "T1",
            "name": "Book the hall",
            "owner": "Ann",
            "duration_days": 3,
            "depends_on": ["T99"],
            "quote": "Ann books the hall."
        }],
        "findings": []
    }

    with pytest.raises(ValueError, match="Unknown dependency"):
        ReviewOutput.model_validate(review)


def test_uncertainty_flags():
    review = {
        "deadline_day": 10,
        "tasks": [{
            "id": "T1",
            "name": "Arrange catering",
            "owner": "Ann",
            "duration_days": 3,
            "depends_on": [],
            "quote": "Catering will take a few days.",
            "confidence": None,
            "flags": ["Duration is not clearly specified"]
        }],
        "findings": []
    }

    validated = ReviewOutput.model_validate(review)

    assert validated.tasks[0].confidence is None
    assert validated.tasks[0].flags == [
        "Duration is not clearly specified"
    ]