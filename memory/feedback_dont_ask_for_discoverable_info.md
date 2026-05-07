---
name: Don't ask for info that's already discoverable in the repo
description: User pushed back on me asking for the GitHub URL when `git remote -v` would have answered it. Check the repo first; ask only what genuinely needs the user's judgment.
type: feedback
---
**Before asking the user a question, check whether a tool call against the repo would answer it.** Asking for info that's one `Bash`/`Read`/`Grep` away wastes the user's attention and reads as not having looked.

**Why:** 2026-04-26. While drafting a project README I asked the user three things at once: which license to use, what the public GitHub URL was, and whether the try-it-out section should target a fresh install. The user replied: *"the rest of the questions you're asking seem to be a bit silly because public GitHub URL you already should have it. License is fine, go ahead and add that."* Two of the three were inappropriate:

- **GitHub URL:** answerable by `git remote -v`. The repo had `origin` configured. I should have read it and just used it.
- **License:** the user didn't care about MIT vs Apache 2.0; they wanted me to pick a sensible default and move on. MIT is the common hackathon choice. I should have picked it without asking.

The only legitimate question was a scope question, and even that one was probably also a "pick the sensible default and move on."

**How to apply, every time I'm about to ask the user something:**

1. **Can a tool call answer it?** Git config (`git remote -v`, `git config user.email`, `git branch -vv`); existing files (`Read`, `Grep`, `Glob`); environment state (`docker ps`, `ls`, `env`). If yes, run the tool first and only ask if the result genuinely needs interpretation.
2. **Does the user actually have a preference here?** Some choices have an obvious sensible default and the user just wants forward motion. License files, default file paths, common naming conventions: pick the conventional answer, mention what I picked, and let the user redirect if they care.
3. **Is the choice reversible?** If yes, just make it and announce the choice. Reversible choices don't need permission; they need transparency.
4. **Batch genuinely-needed questions, don't drip them.** If three questions truly do need the user, ask all three at once. But each one should pass the "tool can't answer plus sensible default doesn't exist plus irreversible" test.

**Telltale warning sign:** I'm about to ask "do you have an X?" where X is a project-state fact. Almost always the answer lives in the repo. Stop, search first.

**Combines with TL;DR plus plain-English rules:** A question that fails the discoverability check pollutes the TL;DR with noise. The user reads "I have three questions" and registers friction before they read the questions. Cut to one (or zero) genuine asks.
