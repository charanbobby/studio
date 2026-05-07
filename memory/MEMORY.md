# Seed memory index (universal cross-project rules)

These are universal cross-project feedback memories carried forward from prior projects. The `seed-memory` skill copies these entries into a new project's `memory/MEMORY.md` on day one.

- [Plain-English communication always](feedback_plain_english_always.md): every response, every turn; pre/post check before sending
- [TL;DR-first format](feedback_tldr_first.md): lead substantial responses with `**TL;DR:**` 2-4 sentences before detail
- [Don't ask for discoverable info](feedback_dont_ask_for_discoverable_info.md): tool-check before asking (git remote, existing files); pick sensible defaults for reversible choices; only ask irreversible questions the repo can't answer
- [Runbooks, not chat instructions](feedback_runbook_markdown.md): multi-step procedures go in committed `.md` with checkboxes
- [Don't oversell scaffolding](feedback_no_overselling.md): setup/install/tool-behaviour is not an achievement; reserve "portfolio-worthy" for engineering we built
- [User drives infra commands](feedback_user_drives_infra.md): document docker/compose/deploy commands; user runs them, not Claude
- [Fail-fast verify](feedback_fail_fast_verify.md): probe any API/env/pattern with a one-off script BEFORE committing to a tracked file
- [Drive fix verification myself](feedback_drive_fix_verification.md): after a code change, I run the verification, not hand the user reload-and-re-run dances
- [Second-invocation check](feedback_second_invocation_check.md): before treating any persistent-state writer as done, answer 4 design questions
- [No unattended / overnight patterns](feedback_no_unattended_patterns.md): permission prompts require human-in-loop; second-LLM help is async dispatch, not autonomy
- [Prompt caching default for Claude API](feedback_prompt_caching_default.md): every Claude API call gets `cache_control: ephemeral` on stable prompt block; off equals defect unless reason stated
- [LLM cost print pattern](feedback_llm_cost_print_pattern.md): copy-paste `_llm_cost_pre` / `_llm_cost_post` helpers + rates dict into any project pipeline; behavioral rule lives in global CLAUDE.md, this is the code template
- [Follow SKILL.md and respect expertise](feedback_skillmd_first.md): phases in order; user is expert in AI/MCP, only suggest domain-gap learning
- [Notebook-first prototyping](feedback_notebook_first.md): for AI/data projects, build inline in Jupyter cells FIRST; extract to modules only after a cell works
- [Telegram Stop hook fires on question/pause signals](feedback_telegram_hook_question_detection.md): hook gates pings on duration OR tool-count OR question/pause phrases
- [`_resume.md` on every break](feedback_resume_file.md): rewrite ephemeral `_resume.md` at repo root on any pause/break signal
- [Fail-fast hooks installable per project](feedback_failfast_hooks.md): two-layer gate (Claude PreToolUse + git pre-commit) enforced via `bash D:/.claude-seed-memory/install-failfast.sh`; opt-in per project via `.failfast.list`