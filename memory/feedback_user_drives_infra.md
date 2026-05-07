---
name: User drives infra commands
description: User wants to run docker/compose/build/deploy commands themselves; document commands in runbooks, don't execute infra for them
type: feedback
---
User drives all infra-level commands (docker compose, build, deploy, push, migrate) themselves. Claude should write the commands into a durable `.md` reference (e.g. `docs/reference/docker-commands.md`) rather than running them on the user's behalf.

**Why:** User wants muscle memory with their own stack, visibility into what runs, and a canonical command reference that outlives any one chat session. Fits their broader "runbooks, not chat" principle.

**How to apply:**

- When a task needs `docker compose up/down/build/logs`, deploys, migrations, or similar infra orchestration, document the command in a project reference file (or create one), then tell the user what to run.
- Exception: mid-debug verification (`docker exec` sanity checks, `docker logs --tail`). These are read-only inspections, fine to run. The rule is about *driving state changes* (up/down/build/deploy), not inspections.
- If the commands file doesn't exist yet, create it before handing off.
- Same principle applies to deploy/push scripts (`deploy.sh`, `push.sh`): default to documenting, not executing.
