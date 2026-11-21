import json
import os
import sys

import anthropic

from pydantic import BaseModel, Field, StrictInt, StrictStr, model_validator

PROMPT = "Review this project plan. Reply with JSON holding deadline_day, tasks and findings."


class ReviewTask(BaseModel):
    id: StrictStr
    name: StrictStr
    owner: StrictStr | None
    duration_days: StrictInt = Field(ge=1)
    depends_on: list[StrictStr]
    quote: StrictStr


class Finding(BaseModel):
    title: StrictStr
    detail: StrictStr
    quote: StrictStr | None


class ReviewOutput(BaseModel):
    deadline_day: StrictInt | None
    tasks: list[ReviewTask]
    findings: list[Finding]

    @model_validator(mode="after")
    def check_dependencies(self):
        ids = [task.id for task in self.tasks]

        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate task IDs in review")

        for task in self.tasks:
            for dep in task.depends_on:
                if dep not in ids:
                    raise ValueError(
                        f"Unknown dependency {dep} in task {task.id}"
                    )

        return self


def valid_quote(quote, plan_text):
    if not isinstance(quote, str):
        return False

    clean_quote = " ".join(quote.split())
    clean_plan = " ".join(plan_text.split())

    return bool(clean_quote) and clean_quote in clean_plan



def check_review_quotes(review, plan_text):
    for i, task in enumerate(review["tasks"]):
        if not valid_quote(task["quote"], plan_text):
            raise ValueError(f"Invalid quote in task {i + 1}")

    for i, finding in enumerate(review["findings"]):
        quote = finding["quote"]

        if quote is not None and not valid_quote(quote, plan_text):
            raise ValueError(f"Invalid quote in finding {i + 1}")

    return review


def review_plan(text, client=None):
    client = client or anthropic.Anthropic()

    reply = client.messages.create(
        model=os.environ.get("REVIEW_MODEL", "claude-sonnet-5-5"),
        max_tokens=16000,
        messages=[{"role": "user", "content": PROMPT + "\n\n" + text}],
    )

    raw_text = "".join(
        block.text for block in reply.content if block.type == "text"
    )

    parsed = json.loads(raw_text)

    validated = ReviewOutput.model_validate(parsed)

    return check_review_quotes(validated.model_dump(), text)

if __name__ == "__main__":
    plan_path, out_path = sys.argv[1], sys.argv[2]
    with open(plan_path) as f:
        review = review_plan(f.read())
    with open(out_path, "w") as f:
        json.dump(review, f, indent=2)
