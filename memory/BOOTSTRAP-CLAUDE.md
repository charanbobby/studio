---
purpose: One-file bootstrap for a new Claude Code project. Drop this in an empty project folder, run the steps, delete the file.
---

# Bootstrap Claude Code project

**TL;DR:** Drop this file in your new (empty) project folder. Run one PowerShell block. After it finishes, your project has: portable memory that Claude Code auto-loads, a visible copy of those files you can open in Explorer, and the 16 universal seed-pack rules already in place. Delete this file when done.

---

## What you get after running

```
<your-project>\
├── BOOTSTRAP-CLAUDE.md           (this file; delete after Step 4)
├── .claude-memory\               (hidden; the working memory Claude reads from)
│   ├── MEMORY.md                 (auto-loads in every Claude session)
│   └── feedback_*.md             (16 seed-pack rules)
└── memory-view\                  (visible copy you can browse in Explorer)
    └── (mirror of .claude-memory)
```

Plus a Windows directory junction at `C:\Users\chara\.claude\projects\<auto-slug>\memory` that points to `.claude-memory`. Claude Code uses the C: side; you read/edit on the D: side.

---

## Step 1: Open PowerShell in this folder

- [ ] In Explorer, right-click inside the project folder, choose **Open in Terminal**
- [ ] Confirm the working directory is the project root: `(Get-Location).Path`

## Step 2: Run the bootstrap

- [ ] Paste the block below as-is. It auto-detects the project name. No edits needed.

```powershell
$proj = (Get-Location).Path
$slug = $proj.Substring(0,1).ToLower() + (
    ($proj.Substring(1) -replace ':', '-') -replace '\\', '-' -replace ' ', '-'
)
$junctionTarget = "C:\Users\chara\.claude\projects\$slug\memory"
$seedSource = "D:\.claude-seed-memory"

# 1. Real working-memory folder (hidden) at the project root
New-Item -ItemType Directory -Path "$proj\.claude-memory" -Force | Out-Null
(Get-Item "$proj\.claude-memory" -Force).Attributes = 'Hidden,Directory'

# 2. C: junction so Claude Code finds it
New-Item -ItemType Directory -Path (Split-Path $junctionTarget) -Force | Out-Null
if (Test-Path $junctionTarget) {
    cmd /c rmdir "`"$junctionTarget`"" | Out-Null
}
cmd /c mklink /J "`"$junctionTarget`"" "`"$proj\.claude-memory`"" | Out-Null

# 3. Copy seed pack into working memory
if (-not (Test-Path "$seedSource\MEMORY.md")) {
    Write-Error "Seed pack not found at $seedSource. Aborting."
    return
}
Copy-Item "$seedSource\*" "$proj\.claude-memory\" -Force

# 4. Visible mirror so you can browse what Claude is reading
New-Item -ItemType Directory -Path "$proj\memory-view" -Force | Out-Null
Copy-Item "$proj\.claude-memory\*" "$proj\memory-view\" -Force

Write-Host ""
Write-Host "Bootstrap complete."
Write-Host "  Working store : $proj\.claude-memory"
Write-Host "  Visible copy  : $proj\memory-view"
Write-Host "  C: junction   : $junctionTarget"
Write-Host ""
Write-Host "Next: open Claude Code in this folder and say 'just bootstrapped, confirm seed pack loaded.'"
```

## Step 3: Add response-format hooks (do this once per project)

These enforce the hard format rules at the hook level so Claude cannot forget them between sessions.

- [ ] Open `.claude/settings.json` in the project folder (create if missing, must be valid JSON `{}` if new)
- [ ] Add the `hooks` block below, merged into the existing JSON object:

```json
"hooks": {
  "UserPromptSubmit": [
    {
      "hooks": [
        {
          "type": "command",
          "command": "echo '{\"hookSpecificOutput\":{\"hookEventName\":\"UserPromptSubmit\",\"additionalContext\":\"HARD FORMAT RULES (every response): 1) Start every response longer than 2 sentences with **TL;DR:** in 2-4 plain-English sentences. 2) Never use em dashes. 3) Plain English always.\"}}'"
        }
      ]
    }
  ]
}
```

**Key hard rules this enforces:**
- Every response longer than 2 sentences opens with `**TL;DR:**` (2-4 sentences, plain English, result-first).
- No em dashes (U+2014) in any generated text - ever. Use commas, semicolons, colons, or parentheses instead.
- Plain English always. No jargon-heavy preamble before the actual answer.

## Step 4: Verify

- [ ] Open `memory-view\MEMORY.md` in Explorer or VS Code; confirm 16 rule entries are listed
- [ ] Open Claude Code in the project folder
- [ ] Say: *"I just bootstrapped this project. Read memory/MEMORY.md and confirm the seed pack loaded."*

## Step 5: Delete this bootstrap file

- [ ] `Remove-Item BOOTSTRAP-CLAUDE.md`

---

## Ongoing workflow: keeping the visible copy in sync

While you work, Claude updates memory files in `.claude-memory` (the hidden working store). When you want to browse what changed, refresh the visible copy:

```powershell
Copy-Item ".claude-memory\*" "memory-view\" -Force
```

Run that any time. It only writes; it never deletes from the visible side, so anything you remove there is your call.

If you want changes you make in `memory-view` to be picked up by Claude, sync the other direction:

```powershell
Copy-Item "memory-view\*" ".claude-memory\" -Force
```

---

## Reverse / cleanup

If you ever need to undo the bootstrap:

```powershell
$proj = (Get-Location).Path
$slug = $proj.Substring(0,1).ToLower() + (
    ($proj.Substring(1) -replace ':', '-') -replace '\\', '-' -replace ' ', '-'
)
$junctionTarget = "C:\Users\chara\.claude\projects\$slug\memory"

if (Test-Path $junctionTarget) { cmd /c rmdir "`"$junctionTarget`"" | Out-Null }
Remove-Item "$proj\.claude-memory" -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item "$proj\memory-view" -Recurse -Force -ErrorAction SilentlyContinue
Write-Host "Project memory removed."
```

---

## If this project has a pipeline that sends tool output to an LLM

This is a global hard rule (also in `~/.claude/CLAUDE.md`) — included here as a reminder at project-setup time.

**Before any tool's output is included in an LLM prompt, measure its worst-case size and add a code-enforced trim if it exceeds ~50 KB.**

Why: two incidents on different projects where tool output entering an LLM bundle caused 10-35x token cost spikes, only caught after the run billed. The pattern: a new tool gets wired up on a small test case, looks fine, then explodes on a domain controller or large disk.

Checklist for any new tool added to an LLM-facing bundle:
- [ ] Run the tool on the worst-case host/input (DC, not workstation; largest disk available). Measure output size.
- [ ] If worst-case output exceeds ~50 KB: add a trim guard in code before the bundle is assembled.
- [ ] Common trim patterns: strip raw bytes / hex blobs the LLM cannot use, filter to relevant rows only (e.g., strip listening sockets from network connection tables), hard cap at N rows sorted by relevance.
- [ ] Add a comment to the trim guard naming the date and pre-trim size so future devs know why it is there.

---

## Notes

- The seed pack source is `D:\.claude-seed-memory\` (the working copy). To update what new projects bootstrap with, edit files there and the next bootstrap will carry the new version.
- The junction is created with a normal user PowerShell prompt (no admin needed). Windows allows directory junctions without elevation.
- `.claude-memory` is hidden so it doesn't clutter your project tree view, but it's still a normal directory; tools that scan all files will find it. Add it to `.gitignore` if you don't want memory in version control.