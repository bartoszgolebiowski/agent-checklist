# Engine Component Instructions

## Guiding Principles

The Engine layer (`engine/`) is responsible for orchestration and execution. It acts as the "CPU" of the system.

### Coordinator vs. Executor

- **Coordinator (`coordinator.py`)**: The **State Machine**.

  - **Role**: Pure logic. Decides _what_ to do next.
  - **Input**: `State`.
  - **Output**: `Decision` (Action type, Skill/Tool name, Reason).
  - **Rule**: Contains **NO** LLM calls and **NO** side effects.

- **Executor (`executor.py`)**: The **LLM Client Wrapper**.
  - **Role**: Execution. Decides _how_ to call the LLM.
  - **Input**: `SkillName`, `context` (dict).
  - **Output**: Structured Pydantic model (the skill's output).
  - **Rule**: Contains **NO** routing logic and **NO** state updates.

### Single Responsibility Principle

- **Coordinator**: "I see the task is in `PLANNING` stage, so I decide we need to run the `PLANNING_SKILL`."
- **Executor**: "I see you want to run `PLANNING_SKILL`. I'll load the template, render it with the context, call the LLM, and give you back a `SkillOutput` object."

## Core Components

### The Coordinator

The Coordinator implements the system's core routing logic.

- **Method**: `next_action(state: State) -> Decision`
- **Logic**: Explicit, non-AI-driven conditional logic (if/else) based on `TaskStage` and `WorkflowState`.
- **Return Values**:
  - `Decision.llm(skill=..., task_id=...)`
  - `Decision.tool(tool=..., task_id=...)`
  - `Decision.complete(...)`
  - `Decision.noop(...)`

### The Executor

The Executor manages the interaction with the LLM.

1.  **Skill Lookup**: Uses `skill_registry` to find the `SkillDefinition`.
2.  **Prompt Rendering**: Calls `definition.render_prompt(context)`.
3.  **LLM Invocation**: Calls `client.invoke(..., output_model=definition.output_model)`.
4.  **Validation**: The `LLMClient` handles Pydantic validation of the response.

## Common Mistakes to Avoid

- **Don't add LLM calls to the Coordinator.** It must remain a fast, deterministic pure function.
- **Don't put routing logic in the Executor.** The Executor just does what it's told.
- **Don't let the LLM decide the next step.** The Coordinator decides the step; the LLM just performs the task.
- **Don't modify state in the Engine.** State updates happen in `memory/state_manager.py`.
