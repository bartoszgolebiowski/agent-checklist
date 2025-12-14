# Architecture Instructions

This document outlines the high-level architectural principles for the Agentic System. The architecture is designed to be modular, state-driven, and easily extensible. It enforces a strict separation of concerns between orchestration, state management, and execution.

## Core Principles

1.  **Separation of Concerns**: The system is divided into distinct layers, each with a single responsibility.

    - **Engine Layer (`engine/`)**: Orchestrates the workflow (`Coordinator`) and handles LLM interactions (`Executor`).
    - **State Management Layer (`memory/`)**: Manages all data structures (`models.py`) and state transitions (`state_manager.py`).
    - **Capabilities Layer (`skills/`)**: Defines the AI's capabilities declaratively (Prompt Templates + Output Schemas).
    - **Tools Layer (`tools/`)**: Wrappers for external services (e.g., Search, APIs).
    - **Prompting Layer (`prompting/`)**: Manages Jinja2 environments and template loading.
    - **LLM Layer (`llm/`)**: Encapsulates LLM client interactions and configurations.

2.  **State-Driven Flow**: The workflow is **not** controlled by the LLM. Instead, a deterministic state machine (`Coordinator`) reads flags from memory to decide the next action. The LLM's role is to provide structured data, not to drive the flow.

3.  **Immutable State**: State (`State`) is treated as immutable. Any modification must be done on a **deep copy** of the state object to ensure predictability and prevent side effects.

4.  **Declarative Capabilities**: AI skills are defined declaratively. They specify _what_ the AI can do (prompt and output structure) but not _how_ to do it (execution logic).

## Request Processing Flow

The system processes tasks through a well-defined, deterministic flow:

1.  **State Analysis**: The `Coordinator` examines the current `State`.
2.  **Decision Making**: Based on the active task's stage and workflow flags, the Coordinator returns a `Decision` (either `LLM_SKILL`, `TOOL`, `COMPLETE`, or `NOOP`).
3.  **Execution**:
    - If **LLM Skill**: The `Executor` loads the skill definition, renders the prompt with context, and calls the LLM to get a structured response.
    - If **Tool**: The system executes the specified tool (e.g., `ToolClient`) using parameters from the state.
4.  **State Update**: The result (LLM output or Tool result) is passed to the `state_manager`, which dispatches it to a specific handler to update the state.

## Memory Update Flow

State modifications are handled centrally and explicitly:

1.  **Output Reception**: The `state_manager` receives the output (from LLM or Tool).
2.  **Dedicated Handler**: The output is routed to a specific handler function (e.g., `update_state_from_skill` or `ingest_tool_results`).
3.  **Deep Copy**: The handler creates a `deepcopy` of the current `State`.
4.  **Modification**: The handler updates the copied state with the new data.
5.  **Return**: The new state object is returned and replaces the old one.

This ensures that all state changes are predictable, traceable, and decoupled from the execution logic.
