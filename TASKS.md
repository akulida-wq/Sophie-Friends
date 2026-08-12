# TASKS — Phase 1: Grey Prototype

Execute in order. One task = one working, committed increment.
No art in this phase: capsule for Sophie, boxes/blobs for world and NPCs.

---

## Task 1 — Project skeleton
Create a Vite + Three.js (TypeScript) project.
- Ground plane, soft ambient + warm directional light, gentle sky color
- Capsule placeholder for the dog "Sophie"
- Game state machine: `EXPLORE / CHOICE / CINEMATIC / PAUSED`
- Folder structure per `docs/03_TECH_SPEC.md`
**Done when:** `npm run dev` shows the scene, state machine logs transitions.

## Task 2 — Movement & follow camera
- Tap/click on ground → Sophie walks there (runs if far), smooth turning
- Third-person follow camera: slightly above and behind, soft lag —
  Sims-like view but following the character
- Works with touch (tablet) and mouse
- Animation state stub: Idle / Walk / Run (visible via color/log for now)
**Done when:** Sophie moves anywhere on the ground, camera follows smoothly, no jitter.

## Task 3 — Interaction & choice panel
- Trigger zones around interactive objects and NPCs (place 3 placeholder
  objects + 1 NPC blob "Bruno")
- Near an object → soft glow pulse (never blink); tap → enter CHOICE state
- CHOICE: controls lock, camera eases in, panel with 2–3 large touch cards
  (icon placeholder + short label), no timer
**Done when:** approaching Bruno and tapping shows a 3-card choice panel; picking a card logs the choice and returns to EXPLORE.

## Task 4 — StoryEngine + SafetyLayer
- StoryEngine reads `src/story/bruno.json` (schema in `docs/03_TECH_SPEC.md`)
  and drives scenes: `choice` scenes and `cinematic` scenes (camera preset +
  actor animation stubs + Sophie line + next). Redirect choices gently loop
  back per JSON.
- SafetyLayer: 10s inactivity in EXPLORE/CHOICE → Sophie hint (highlight one
  object + soft line); 2 avoidant choices in a row → jump to soft branch id
  from JSON.
- Create `bruno.json` with PLACEHOLDER content for scenes 1–3 only
  (Gentle Arrival → Recognize the Feeling → Acknowledge). Full 8-scene JSON
  arrives later — build the engine so swapping the JSON needs zero code changes.
**Done when:** the mission plays scenes 1–3 end-to-end from JSON; editing a line in JSON changes the game without touching code.

## Task 5 — Cinematic system
- CinematicCamera presets: `wide`, `closeup(actor)`, `over_shoulder`
- CINEMATIC state: disable controls → slow tween to preset → play actor
  animation stubs + Sophie line (text bubble for now) → ease back to follow
  camera → EXPLORE
- Transitions slow and soft — no cuts, no shake, no flash
**Done when:** after a choice, a short staged scene plays and control returns smoothly.

---

When Task 5 is done → follow the "When ALL tasks are done" instruction
in `CLAUDE.md`.
