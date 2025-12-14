# Memory Component Instructions

## Guiding Principles

The Memory layer (`memory/`) is the stateful core of the system. It defines the structure of all data and provides the logic for how that data is modified.

### The State

The global state is defined in `models.py` as `State` (or `AgentState`). It is a composite of several sub-models:

| Layer        | Model            | Purpose                                                |
| :----------- | :--------------- | :----------------------------------------------------- |
| **Core**     | `CoreMemory`     | Fixed identity and persona (read-only).                |
| **Semantic** | `SemanticMemory` | Long-term knowledge, domain preferences.               |
| **Episodic** | `EpisodicMemory` | History of past runs/events.                           |
| **Workflow** | `WorkflowState`  | Flags, counters, and limits driving the state machine. |
| **Working**  | `WorkingMemory`  | Active tasks, tool results, and current context.       |

### Immutability & Updates

State must be treated as **immutable**.

- **Pattern**: `new_state = deepcopy(old_state)`
- **Location**: All update logic resides in `state_manager.py`.
- **Dispatch**: `update_state_from_skill` routes output to specific handlers based on `SkillName`.

### Structured Data Models

All data structures must be Pydantic `BaseModel`s.

- **Type Safety**: Use strict type hints (`List[str]`, `Optional[int]`).
- **Defaults**: Use `Field(default_factory=list)` for mutable defaults.
- **Validation**: Pydantic ensures data integrity at runtime.

## State Management Logic

### Initialization

- `create_initial_state(...)` in `state_manager.py` creates a fully populated state tree.
- Ensure all lists/dicts are initialized to empty values, never `None` (unless explicitly optional).

### Update Handlers

- Each Skill has a corresponding handler function (e.g., `_update_from_skill_name`).
- Handlers should:
  1.  Accept `(state, output)`.
  2.  Deepcopy the state.
  3.  Map fields from `output` (the Skill's result) to `state` (the Memory).
  4.  Update workflow flags (e.g., advance `TaskStage`).
  5.  Return the new state.

## Common Mistakes to Avoid

- **Don't mutate `state` in place.** Always `deepcopy`.
- **Don't put logic in `models.py`.** Models are for data definition only.
- **Don't mix layers.** Workflow flags go in `WorkflowState`, not `SemanticMemory`.
- **Don't forget `from __future__ import annotations`.**
