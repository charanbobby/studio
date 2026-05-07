---
name: Notebook-first prototyping, modules come later
description: For AI/data/pipeline projects, build inline in a Jupyter notebook cell-by-cell FIRST; extract to modules only after a cell works. Matches SKILL.md Phase 3 literally.
type: feedback
---
For any project that prototypes a data or AI pipeline, build every step inline in a Jupyter notebook first, one cell per step, so the user can run cell-by-cell, inspect intermediate output, and iterate without module boilerplate in the way. Only promote code to `<package>/*.py` modules AFTER a cell proves the step works.

**Why:** The user's SKILL.md Phase 3 is unambiguous: *"Notebooks let me run each step independently, inspect intermediate state, and iterate without restarting servers."* First surfaced when I structured early work as `schemas.py` then `llm.py` then `prompts.py` then notebook (modules-first), which inverts the phase. The user wants to SEE each step run before it gets abstracted. The notebook is also the place where "prompt quality is the bottleneck" gets discovered.

**How to apply:**

- When a runbook or plan lists modules before a notebook, flip the order: notebook-first, modules-later.
- Per-cell pattern: imports plus one phase of logic plus visible output (`print` / dataframe / `json.dumps(indent=2)`). No hidden state, no helper module imports for the cell's core logic.
- Schemas (Pydantic models), prompts, LLM calls, client wiring all start inline in notebook cells.
- Exceptions (things that *must* be standalone files from the start):
  - Subprocess servers (e.g. MCP servers spawned via `docker exec -i ...`). Can't live in a notebook.
  - Anything that needs to be importable by an external process.
- Once a cell stabilizes (user has run it, seen output, approved), extract to a module and replace the cell with a thin import. Don't extract prematurely.
- When writing a runbook for a new slice, put the notebook as Step 1 (or right after container prereqs), not Step 7.
- **Bundling rule (added 2026-04-20):** when promotion becomes attractive ("notebook is getting large"), check whether the NEXT slice already plans to rewrite the cell's API. If yes, bundle the extraction with that slice's refactor: single migration, not two. Mid-prototyping module extraction locks in an API that's about to change. Bundling extraction with the next schema-shifting slice lets the modules land in their final shape, with real `pytest` tests from day one, and preserves the notebook as the narrative artifact rather than a competing code home.

**Skip this rule when:** the project has no notebook component (e.g. CLI tool, web service, library). It's specifically for projects where exploratory prototyping is the right mode.
