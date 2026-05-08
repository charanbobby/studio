# Cover note template (CSC Generation submission)

Copy/paste into the submission email. Replace the bracketed fields. Keep it to one screen.

---

Hi [recruiter name],

Submitting my AI Solutions Engineer take-home for CSC Generation. Three components below.

**Component A: Working build**
- Repo: [https://github.com/<you>/sri-studio-csc](https://github.com/<you>/sri-studio-csc) (read access granted to [assessor's GitHub])
- Live URL: https://studio.sshub.dev/
  - Username: `csc`
  - Password: `csc2026`
- Daily cost cap is set at $5 USD; please feel free to generate as many reels as you'd like within that budget.
- The reels speak in my own voice (Instant Voice Clone via ElevenLabs). The continuity hook for the walkthrough below.
- Try the "Past runs" link in the header to see prior runs (including a couple of mine).

**Component B: Walkthrough video (12-14 min)**
- [Loom or YouTube link]
- Covers: project framing, architectural choice (LangGraph over n8n), 4-node pipeline + mandatory human-approval gate, fail-fast probe matrix, live demo with one Approve + one Reject, observability via Langfuse Cloud, production deploy, what's next.

**Component C: AI Questionnaire**
- Attached as `questionnaire-final.md` (or [Drive link]).
- Lead example for Q3 / Q4 / Q6 / Q7 / Q8 is this build itself; supporting examples cite prior projects.

**One ask:** if my Cloudflare DNS is slow to propagate to your local resolver, hit `https://46.62.255.66/` with the same credentials and the host header `studio.sshub.dev` (or just wait 5 min). Cert is valid Let's Encrypt.

Happy to walk through any of it live; available [your availability].

Thanks,
[your name]

---

## Notes for you (not part of the email)

- Don't send the `sri / admin` credentials to CSC. The `csc / csc2026` account is the one that gets shared.
- After the interview window, revoke `csc` per `docs/submission-checklist.md` step 10.
- If you want to add a paragraph about the Langfuse dashboard so they can verify the run history themselves, say:
  > For traceability: every run is linked to a Langfuse session (input messages, model output, token usage, USD cost are all captured per call). I can grant read access to the project dashboard on request.
