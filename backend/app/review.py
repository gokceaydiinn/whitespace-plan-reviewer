import json
import os
import sys

import anthropic
from openai import OpenAI
from pydantic import BaseModel, Field, StrictInt, StrictStr, model_validator

def get_provider():
    return os.environ.get("REVIEW_PROVIDER", "anthropic").lower()

PROMPT = """
Review this event plan and return only valid JSON.

The JSON must have:
- deadline_day: integer or null
- tasks: list of tasks
- findings: list of findings

Each task must have:
id, name, owner, duration_days, depends_on, quote

Each finding must have:
title, detail, quote

Use unique task IDs. Dependencies must refer to existing task IDs.
depends_on must always be a JSON array.
Use [] when a task has no dependencies.
Use ["T1"] when a task depends on T1, never "T1" or null.
Do not invent dependencies that are not supported by the plan.
Every task duration must be a positive integer.
Use null for an owner if no person is named.

Copy each quote directly from the plan. Do not paraphrase quotes.
If information is missing or unclear, do not silently assume it is certain.

For each task, also include:
- flags: a list of short explanations of uncertainty
- confidence: null

Flag unclear durations, owners or dependencies.
Convert clearly stated weeks to days using 1 week = 7 days.
Do not flag a duration solely because it is expressed in weeks.
When a duration is unclear, explain this in flags.
Do not present an estimated duration as confirmed.
When an owner is missing, use null and add an owner flag.
When a dependency is unclear, flag it instead of inventing a dependency.
Keep the required fields even when information is uncertain.
Use findings to explain missing information or inconsistencies.
Use task-level flags only for uncertainty specific to that task.
If the same uncertainty applies to the whole plan, report it once as a finding instead.
Do not repeat the same general warning across every task.

Return JSON only, with no markdown formatting.

Plan:
"""



class ReviewTask(BaseModel):
    id: StrictStr
    name: StrictStr
    owner: StrictStr | None
    duration_days: StrictInt = Field(ge=1)
    depends_on: list[StrictStr]
    quote: StrictStr
    confidence: float | None = Field(default=None, ge=0, le=1)
    flags: list[StrictStr] = Field(default_factory=list)


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
    provider = get_provider()

    if provider == "openrouter":
        client = client or OpenAI(
            api_key=os.environ["OPENROUTER_API_KEY"],
            base_url="https://openrouter.ai/api/v1",
        )

        reply = client.chat.completions.create(
            model=os.environ.get(
                "REVIEW_MODEL", "nvidia/nemotron-3.5-super-vl:free"
            ),
            messages=[
                {"role": "user", "content": PROMPT + "\n\n" + text}
            ],
        )

        raw_text = reply.choices[0].message.content

    elif provider == "anthropic":
        client = client or anthropic.Anthropic()

        reply = client.messages.create(
            model=os.environ.get("REVIEW_MODEL", "claude-sonnet-5-5"),
            max_tokens=16000,
            messages=[
                {"role": "user", "content": PROMPT + "\n\n" + text}
            ],
        )

        raw_text = "".join(
            block.text for block in reply.content if block.type == "text"
        )

    else:
        raise ValueError(f"Unknown review provider: {provider}")

    if not raw_text:
        raise ValueError("Model returned an empty response")

    parsed = json.loads(raw_text)
    validated = ReviewOutput.model_validate(parsed)

    return check_review_quotes(validated.model_dump(), text)

if __name__ == "__main__":
    plan_path, out_path = sys.argv[1], sys.argv[2]

    with open(plan_path) as f:
        review = review_plan(f.read())

    with open(out_path, "w") as f:
        json.dump(review, f, indent=2)