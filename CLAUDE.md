# Sophie & Friends — Vertical Slice (Web Mock)

Children's emotional-resilience game prototype (ages 4–9, war-affected children
in Ukraine). Tech: Vite + Three.js (TypeScript). This is a pitch mock; assets
(GLB) and story JSON will later be reused in a Unity production build.

## Before any work
Read, in this order:
1. `docs/01_PROJECT_CONTEXT.md` — what the game is, characters, safety rules
2. `docs/02_GAME_DESIGN_MVP.md` — the vertical slice design
3. `docs/03_TECH_SPEC.md` — architecture and story JSON schema
4. `TASKS.md` — your task queue

Then execute tasks from `TASKS.md` strictly in order, one at a time.

## Hard rules (override everything)
- SAFETY LAYER: no sudden sounds, no flashing/blinking, no fail language
  anywhere in UI or code-facing text (no "wrong / failed / lose / game over"),
  no timers on choices, pause/exit always available.
- Story content lives ONLY in `src/story/*.json` — never hardcode dialogue,
  choices or branching in code.
- Max 3 choice options, big touch-friendly cards (min ~25% of screen height),
  icons over text.
- All story branches must converge to a calm resolution.
- All UI text and Sophie lines: English (pitch version). Keep lines as ids in
  JSON where possible.
- Target device: tablet, touch-first, 60fps. Mouse must also work for desktop
  demo.

## Architecture
Separate systems: `core / player / camera / interaction / dialogue / story /
safety / audio`. Never put game logic into one giant file. Placeholder
primitives (capsule dog, box world, colored blobs for NPCs) until GLB assets
arrive — do not generate or download any art.

## Workflow per task
1. Implement the task.
2. Verify it runs (`npm run dev`, no console errors).
3. `git commit` with a short message.
4. Print a 3–5 line summary: what works now + how to test it by hand.
5. Move to the next task only after the current one runs.

If something is ambiguous — pick the simplest option consistent with the safety
rules and note the assumption in the summary. Do not expand scope beyond the
current task.

## When ALL tasks in TASKS.md are done
Stop and print exactly this message:

"PHASE 1 COMPLETE. Серый прототип готов. Проверь вручную: движение, камеру,
выбор, cinematic-переходы. Дальше вернись в чат Claude (web) за полным
bruno.json (8 сцен) и задачами Фазы 3 (импорт GLB из Blender)."
