---
name: Telegram Stop hook fires on question/pause signals (no behavior dependency)
description: Stop hook (continue-from-phone.js) gates Telegram pings on duration/tool-count OR question/pause-for-input phrases; ensures user is paged when Claude is genuinely waiting
type: feedback
---
The user's `Stop` hook at `C:/Users/chara/.claude/hooks/continue-from-phone.js` decides whether to ping Telegram for a "Claude is waiting on you" event. It used to gate purely on **turn duration >= 60s** OR **tool call count >= 3**. Short, tool-light "I'm waiting for direction" turns silently exited without paging.

**Fix landed 2026-04-25:** added a third OR'd gate that detects when the assistant message is *asking for input*. Triggers fire on:

- A trailing `?` at the end of the message (after trim)
- Phrase matches in the last ~500 chars: `Want me to`, `Should I`, `Shall I`, `Which way`, `Which one`, `let me know`, `or pause`, `or proceed`, `continue or`, `pause or`, `tell me`, `stand by`, `standing by`, `paste here`, `review and`, `do you want`, `what do you want`, `preference?`, `verdict?`, `thoughts?`

**Why this rule is hard, not soft:**

- User stated 2026-04-25: *"I keep forgetting things, so we need to keep that persistent."* Memory-based behavioral rules drift; the user explicitly said they don't trust them on this kind of thing. Putting the enforcement in the hook itself means my forgetfulness can't break it.
- The pre-fix gates filtered out the EXACT moments the user most needed to be paged (short questions). Telegram fired reliably for "permission" prompts but not for "Claude paused awaiting answer," which was the higher-value signal.

**How to apply:**

- The hook is now self-enforcing. I do NOT have to remember to make 3+ tool calls just to trigger it; ending with a clear question or recognised pause-phrase is enough.
- Belt-and-suspenders: when I am genuinely waiting for input, end the message with either a `?` or one of the recognised phrases. This gives the hook a clean signal AND makes the intent unambiguous to a human reader.
- If the user introduces a NEW pause phrase they use repeatedly (e.g. "use 'go ahead?' to mean proceed"), update the regex in the hook, not just memory.
- Probe before changing the regex: a stdlib Node test (~12 cases) takes 30 seconds and catches false positives.

**Where this lives:**

- Hook source: `C:/Users/chara/.claude/hooks/continue-from-phone.js` (Stop hook, registered in `~/.claude/settings.json`)
- Detection logic: lines around the `askingForInput` variable in `main()`
- Server endpoint the hook posts to: `https://approve.sshub.dev/continue` (see `CONTINUE_URL`)

**Edge cases:**

- A `?` inside a code block / regex literal at the end of a message will trigger the hook. False positive, harmless extra ping.
- A long status update with no question and no listed phrase but lots of tool calls still fires via the duration/tool-count gates; that hasn't changed.
- `CLAUDE_REMOTE_OFF=1` disables the hook entirely; `CLAUDE_APPROVE_TOKEN` unset is a no-op. Both are still honoured.
