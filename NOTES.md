# Notes

## Time spent

Approximately 2.5 hours.

## What I did

I started by breaking down the assignment into three priorities: reliable scheduling, trustworthy AI extraction, and a clear interface for the person reviewing the plan.

I focused on the backend first. I used OR-Tools to schedule tasks while respecting dependencies and making sure the same person isn't assigned overlapping work. I deliberately separated AI extraction from scheduling so that the model interprets the plan, while the actual calculations remain deterministic.

Reliability was particularly important to me. My bachelor's thesis focused on AI-driven information extraction, and one of my main takeaways was that plausible AI outputs still need validation. I applied that here by validating the JSON structure and checking that extracted quotes actually appear in the original document.

For the interface, I focused on making the results useful rather than just displaying information. I added a schedule overview, specific findings with suggested actions, expandable source evidence, and editable tasks that users can reschedule.

## What I cut and why

I prioritized a complete, working review flow over additional features. I left out user accounts, persistent edits, and advanced timeline visualizations.

I also kept the interface relatively simple and followed the WhiteSpace brand guidelines. I wanted users to understand the schedule and identify what needs attention without navigating a complicated dashboard.

## What is not ready

Edits currently exist only within the browser session and are not saved permanently.

Plans with missing or conflicting deadlines can be reviewed and scheduled, but the interface does not yet support entering a new deadline and recalculating against it.

The AI extraction process is not completely reliable on every attempt. Invalid quotes or incorrectly structured responses are rejected rather than accepted silently.

The scheduler also has a time limit, meaning a feasible solution is not always guaranteed to be proven optimal.

## What I would do next and a rough estimate

With another 2–3 hours, I would improve the review workflow by allowing users to edit the deadline, save their changes, and get clearer validation messages.

I would also add more tests for missing information, conflicting dependencies, and AI extraction edge cases. A compact timeline view would be my next UI improvement once the core workflow is more robust.

## How I used AI tools

I independently broke down the requirements, defined the priorities, planned the architecture, and made the main technical and product decisions.

I used AI assistance to help write and refine code, compare implementation options, troubleshoot errors, and improve the interface. I reviewed the changes, tested the results, and adjusted the implementation when something didn't behave as expected.

I treated AI as a development assistant rather than a replacement for deciding how the application should work.

## Environment variables my review command needs

The review CLI supports two AI providers:

- **OpenRouter:** `REVIEW_PROVIDER=openrouter` and `OPENROUTER_API_KEY`
- **Anthropic:** `REVIEW_PROVIDER=anthropic` and `ANTHROPIC_API_KEY`

`REVIEW_MODEL` can optionally be set to select a specific model. API keys are provided through environment variables and are not stored in the repository.