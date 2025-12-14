# AI Checklist Agent

A deterministic, state-driven assistant that converts natural language goals into actionable checklists, refines them via dialogue, tracks progress, and produces completion summaries backed by conversational context.

## Highlights

- **Deterministic state machine**: `Coordinator` selects the next skill/tool purely from `ResearchState` flags.
- **Structured skills**: Each agent capability (checklist generation, refinement, progress interpretation, summaries) is defined declaratively via Jinja templates and typed Pydantic outputs.
- **Hierarchical plans**: Primary checklist items grow proactive sub-checklists only when a step is broad, giving up to five focused subtasks where extra structure is helpful.
- **Immutable memory updates**: `state_manager` deep-copies state for every mutation, ensuring predictable transitions that mirror the business flow.
- **Persistent history**: Finalized checklists (with refinement context and progress logs) are stored as JSON snapshots under `storage/checklists/` by default.

## Project Layout

- `agent_checklist/domain.py` – enums and decision primitives used across the engine.
- `agent_checklist/memory/` – Pydantic models plus the `state_manager` responsible for all transitions.
- `agent_checklist/skills/` – skill schemas, registry, and prompt templates (`prompting/jinja/...`).
- `agent_checklist/engine/` – `Coordinator` (state machine) and `Executor` (LLM runner).
- `agent_checklist/llm/` – OpenAI client wrapper with structured output enforcement.
- `agent_checklist/services/persistence.py` – checklist snapshot repository.
- `agent_checklist/app.py` – `ChecklistAgent` façade that orchestrates the workflow.

## Quick Start

1. Install dependencies (Python 3.11+):
   ```bash
   pip install -e .
   ```
2. Configure environment variables:
   - `OPENROUTER_API_KEY` or `OPENAI_API_KEY` – required to call the LLM API (OpenRouter preferred).
   - `OPENROUTER_MODEL` or `OPENAI_MODEL` (optional, default `openai/gpt-4o-mini`).
   - `OPENROUTER_TEMPERATURE` or `OPENAI_TEMPERATURE` (optional, default `0.2`).
   - `OPENROUTER_BASE_URL` or `OPENAI_BASE_URL` (optional, default `https://openrouter.ai/api/v1`).
   - `CHECKLIST_STORAGE_DIR` (optional, default `storage/checklists`).
3. Use the agent:

   ```python
   from agent_checklist import ChecklistAgent

   agent = ChecklistAgent.from_env()
   agent.ingest_description("Plan the product launch for Q2")
   decision = agent.run_planned_action()  # generates the initial checklist

   # Present agent questions to the user, then feed answers back
   agent.record_refinement_feedback("Budget finalized; launch event depends on venue approval.")
   agent.run_planned_action()  # incorporates refinements

   agent.approve_checklist()
   path = agent.save_checklist()
   print(f"Checklist persisted at {path}")
   ```

`run_planned_action()` always returns a `Decision`. When the decision type is `LLM_SKILL`, the executor will automatically run the corresponding prompt and update the state. When it is `DecisionType.NOOP`, the workflow is waiting on user input (answers, approvals, or progress updates).

## Manual Session Script

To run an end-to-end interactive session (with real LLM calls) that mirrors the business flow, execute [examples/manual_session.py](examples/manual_session.py):

```bash
python examples/manual_session.py
```

The script loads environment variables from `.env`, walks you through description capture, refinement, approval, persistence, and optional progress tracking so you can observe how the agent updates state in real time.

## State Machine Coverage

The deterministic phases mirror the business specification:

1. **Initialization** – ingest description (`GENERATE_INITIAL_CHECKLIST`).
2. **Refinement** – ask up to three clarifying questions, then merge responses (`INCORPORATE_REFINEMENTS`).
3. **Finalization** – user approves, the checklist is persisted via `ChecklistRepository`.
4. **Active Tracking** – natural language progress updates are interpreted (`INTERPRET_PROGRESS_UPDATE`), logged, and acknowledged.
5. **Completion** – once every item is complete, the summary skill generates a narrative closure stored in memory and shared with the user.

Clarifications, additional items, or unmarking progress are handled through the memory/state helpers, ensuring every speech act is logged in `conversation_log` and `progress_log`.

## Persistence Format

Persisted snapshots follow `ChecklistArtifact`:

- task description and creation timestamp
- every checklist item with status, notes, and its nested sub-checklist (each sub-item retains its own status)
- refinement exchanges for traceability
- chronological progress log entries
- completion notes / agent summary

Files are JSON-encoded and suitable for audit or future retrieval through `ChecklistRepository.load()`.

## License

MIT License

Copyright (c) 2025 Bartosz Golebiowski

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
