# Sample reels

End-to-end runs from the deployed system at https://studio.sshub.dev/, generated via Playwright-driven Browse.

Each subdirectory holds:
- `reel.mp4` (vertical 1080x1920, voice-cloned narration, burn-in captions)
- `plan.json` (the auditable ScriptPlan the human approved or rejected)
- `intent.json` (ExtractedIntent from the brief)
- `cost.json` (per-phase ledger; total cost in USD)

## f7355e2091dd: Sri Studio launch teaser
- Brief: "A 5-second teaser for Sri Studio: vertical reels generated in your own voice, energetic launch energy"
- Outcome: 3.3s reel, 2 scenes, $0.0312 total

## 5998fdd3a75b: Sur La Table spring sale (CSC portfolio brand)
- Brief: "Sur La Table spring kitchen sale, energetic, food-focused, build excitement around new copper cookware"
- Outcome: 6.6s reel, 2 scenes, $0.0541 total

## 41826991cc8a: Cozy autumn coffee shop (REJECTED)
- Brief: "Cozy autumn coffee shop, calm vibes, latte art close-ups"
- Outcome: human-rejected at the approval gate
- Cost: $0.0058 (only Extract + Plan; no Execute APIs fired)
- Demonstrates the mandatory human-approval gate bounding cost when the
  plan does not match intent.
