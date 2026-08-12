# Claude Code — промты по шагам

## Подготовка
1. Создай папку проекта, положи в неё `CLAUDE.md` (текст ниже) и файлы `01_PROJECT_CONTEXT.md`, `02_GAME_DESIGN_MVP.md`, `03_TECH_SPEC.md`.
2. Запусти `claude` в папке. Дальше — промты по одному, коммить после каждого рабочего шага.
3. Правило из GPT-инфо (согласен): **никогда не проси «сделай игру как Sims»** — только итеративно, один системный кусок за раз.

## CLAUDE.md (положи в корень проекта)
```markdown
# Sophie & Friends — Vertical Slice

Children's emotional-resilience game prototype (ages 4-9, war-affected children in Ukraine).
Read 01_PROJECT_CONTEXT.md, 02_GAME_DESIGN_MVP.md, 03_TECH_SPEC.md before any task.

## Hard rules (override everything)
- SAFETY LAYER: no sudden sounds, no flashing, no fail language anywhere
  (no "wrong/failed/lose"), no timers, pause/exit always available.
- Story content lives ONLY in /src/story/*.json — never hardcode dialogue or branching.
- Max 3 choice options, big touch-friendly cards, icons over text.
- All branches must converge to a calm resolution.
- Target device: tablet, touch-first, 60fps.
- All UI text, Sophie lines and story content in English (pitch version).
- Keep everything portable: all art as GLB, all narrative in JSON —
  these assets will later be reused in a Unity production build.

## Architecture
Keep systems separate: core / player / camera / interaction / dialogue / story / safety / audio.
Never put game logic into one giant file.

## Workflow
Small iterations. After each feature: it must run, then stop and summarize.
Placeholder primitives (capsule dog, box world) until GLB assets arrive.
```

## Промты (веб-путь: Three.js + Vite)

**#1 — Каркас**
```
Create a Vite + Three.js (TypeScript) project for a 3D narrative game prototype.
Set up: a ground plane, soft ambient + directional light, a capsule placeholder
for the dog "Sophie", and a game state machine with states EXPLORE / CHOICE /
CINEMATIC / PAUSED. No art, no story yet. Architecture per 03_TECH_SPEC.md.
Make it run with `npm run dev`.
```

**#2 — Движение и камера**
```
Add player control: tap/click on the ground moves Sophie there (walk, run if far),
with smooth turning. Add a third-person follow camera: slightly above and behind,
soft lag, like The Sims but following the character. Must work with touch on tablet.
Placeholder animation states: Idle / Walk / Run (log or color change for now).
```

**#3 — Интеракции и панель выбора**
```
Add an interaction system: trigger zones around interactive objects and NPCs;
when Sophie is near, the object glows with a soft pulse (never blink). Tapping it
enters CHOICE state: controls lock, camera eases in, and a choice panel appears —
2-3 large touch cards (min 25% of screen height, icon-first, minimal text).
No timers on choices.
```

**#4 — StoryEngine + safety layer**
```
Add a StoryEngine that reads /src/story/bruno.json (schema in 03_TECH_SPEC.md)
and drives scenes: choice scenes and cinematic scenes (camera preset + actor
animations + Sophie line + next). Redirect choices must gently loop back per the
JSON. Add SafetyLayer: after 10s of inactivity in EXPLORE/CHOICE, Sophie hint
(highlight one object + soft line); after 2 avoidant choices, jump to the soft
branch id from JSON. Create bruno.json with placeholder content for scenes 1-3.
```
→ **После этого шага вернись в чат к Claude** — сверим серый прототип и я дам полный bruno.json по всем 8 сценам клиентского скрипта.

**#5 — Cinematic-система**
```
Add a CinematicCamera system with presets: wide, closeup(actor), over-shoulder.
CINEMATIC state: disable controls, tween camera to preset, play actor animations
and Sophie's line, then ease back to follow camera and return to EXPLORE.
Transitions must be slow and soft — no cuts, no shake.
```

**#6 — Импорт GLB**
```
Replace the capsule with /assets/sophie.glb (animations: Idle, Walk, Run, Sit,
Happy, Sad, Curious, Sniff, Bark, TailWag). Wire animation states to movement
and to story actions. Add bruno.glb and environment.glb the same way.
Crossfade between animation clips (0.3s), never snap.
```

**#7 — Аудио и полировка**
```
Add layered audio: calm ambient loop that warms up as bruno_state progresses;
soft rounded UI sounds; Sophie voice lines from /assets/voice (with subtitles
optional). Volumes low by default. Add pause/exit button (top corner, always
visible). Final pass: lighting warmth shift across the mission, gentle reward
glow at resolution. Verify: no flashing, no harsh sounds anywhere.
```

## Если выбран Godot-путь
Промты те же по смыслу, замена в #1: «Create a Godot 4 project (GDScript)...», сцены = .tscn, структура из GPT-инфо (scenes/scripts/assets/story) годится как есть. Скажи Claude в чате — переведу все промты под Godot.
