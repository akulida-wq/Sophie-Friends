# TASKS — Phase 2–3: Full Story + Assets

Положи этот файл в корень проекта как `TASKS_PHASE3.md`, а `bruno.json` —
в `src/story/bruno.json` (замени плейсхолдерный).

Стартовый промт для Claude Code:

```
Read CLAUDE.md and TASKS_PHASE3.md. The full story file src/story/bruno.json
has replaced the placeholder. Execute the tasks in TASKS_PHASE3.md strictly
in order with the same workflow as before (implement -> run -> commit ->
summary). When all tasks are done, print the final message from the bottom
of TASKS_PHASE3.md.
```

---

## Task 6 — Full mission integration (можно запускать СРАЗУ, Blender не нужен)
Extend the StoryEngine to support the full bruno.json:
- New scene types: `minigame` (drag object to target / tap object, success on
  any option, hesitation fallback after N sec from JSON) and `end_menu`
  (recap line + 3 large option cards; "Visit another friend later" shows a
  soft "coming soon" state — never a lock icon or error styling).
- `intro_actions` / `setup_actions` / `outcome_actions` on choice scenes.
- `advance: tap_cue` mode for cinematic scene 1 (pulsing heart cue on Bruno).
- `bruno_state` visual stub: withdrawn/noticed/named/accepted/trying/wobble/
  connected → for now tint Bruno's placeholder color from cool gray-blue to
  warm blue and raise his "head" (scale/rotate stub). Real animations come
  with GLB.
- `simplify_after_misses`: after 2 wrong feeling picks, show only 2 options.
- SafetyLayer: avoidant streak (choices with `"avoidant": true`) >= 2 → jump
  to `soft_support` scene per the safety block in JSON.
**Done when:** миссия проходится целиком из JSON: все 8 сцен + soft_support, все редиректы мягкие, состояние Бруно видимо меняется.

## Task 7 — Sophie GLB
Replace the capsule with `/public/assets/sophie.glb`.
- Wire clips: Idle, Walk, Run, Sit, Happy, Sad, Curious, Sniff, Bark, TailWag
- Movement → Idle/Walk/Run automatically; story `anim` actions → clips by name
- Crossfade 0.3s, never snap; graceful fallback if a clip is missing
  (log a warning, keep Idle — no crash)
**Done when:** собачка ходит/бежит со своими анимациями, story-сцены дёргают клипы по имени.

## Task 8 — Bruno, friends & environment GLB
- `/public/assets/bruno.glb` (clips: IdleSad, IdleOpen, Walk, HandToChest,
  SmallWave, SitAlone, TryJoinClumsy, TryAgainSucceed, PlayIncluded)
- `/public/assets/environment.glb` (playground) replaces box world; keep
  navigation working on the new ground
- `bruno_state` now drives real animation blending (IdleSad → IdleOpen arc)
  + scene color temperature: cool at start, warming to resolution
**Done when:** вся миссия играется в финальном арте, арка Бруно читается без текста.

## Task 9 — Audio & final polish
- Layered ambient: calm loop, warms/lifts as bruno_state progresses
- Soft rounded UI sounds (low volume by default), Sophie voice line hooks
  from `/public/assets/voice/{line_id}.mp3` with graceful fallback to text
  bubble if file missing
- Pause/exit button top corner always visible; reward warm-glow at resolution
- Final safety pass: verify no flashing, no harsh sounds, no fail language
**Done when:** прогон миссии от заставки до calm exit ощущается спокойным и цельным.

---

When Task 9 is done, stop and print:

"PHASE 3 COMPLETE. Мок играется целиком. Вернись в чат Claude за финальным
чеклистом упаковки для заказчика (деплой-ссылка, walkthrough, передача)."

---

## Напоминание себе (не для Claude Code)
Task 6 запускай сейчас. Параллельно — Blender по гайду
`for-me/04_BLENDER_SOPHIE_GUIDE.md`: Софи (модель→риг→10 анимаций→GLB),
потом Бруно (он сильно проще), потом площадка. Проверяй каждый GLB в
gltf-viewer.donmccurdy.com ПЕРЕД тем как несёшь в проект. Blender подключён
к Claude через MCP — блокауты и расстановку ключей проси промтами.
