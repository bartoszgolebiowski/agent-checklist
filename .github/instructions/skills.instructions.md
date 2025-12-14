# Skills Component Instructions

## Guiding Principles

The Skills layer (`skills/`) contains the **declarative definitions** of the AI's capabilities.

### What is a Skill?

A Skill is defined by the `SkillDefinition` class (`definitions.py`) and consists of:

1.  **Name**: A unique `SkillName` enum value.
2.  **Prompt Template**: A Jinja2 template path (e.g., `skills/skill_name.j2`).
3.  **Output Model**: A Pydantic model class defining the expected structure (e.g., `SkillOutput`).

### Core Rule: No Execution Logic

- Skills are **data**, not code.
- They do **not** have `.execute()` methods.
- They do **not** call APIs.
- They simply define: "If you want to do X, ask the LLM _this_ and expect _that_ back."

## Creating New Skills

To add a new capability:

1.  **Define Output Model**: Create a Pydantic model in `skills/models.py`.
    - Must include `ai_response: str` for the conversational part.
    - Must include structured fields for the data you want to extract.
2.  **Create Template**: Add a `.j2` file in `prompting/jinja/skills/`.
    - Inherit from/include memory templates.
    - Be explicit about the task.
3.  **Register Skill**: Add a `SkillDefinition` to `skills/definitions.py`.
    - Add the name to `SkillName` enum (`domain.py`).
    - Register in `ALL_SKILLS` list.
4.  **Handle State**: Create a handler in `memory/state_manager.py` to process the output.
5.  **Add Routing**: Update `Coordinator.next_action` to trigger this skill.

## Common Mistakes to Avoid

- **Don't put logic in `SkillDefinition`.**
- **Don't hardcode prompts in Python.** Use Jinja2.
- **Don't reuse Output Models.** Each skill should usually have its own specific output structure.
- **Don't forget to register the skill.** The Executor won't find it otherwise.
