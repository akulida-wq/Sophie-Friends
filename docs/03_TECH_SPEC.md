# Tech Spec

> **РЕШЕНИЕ ПРИНЯТО:** мок — Вариант A (Three.js, веб). Язык интерфейса/озвучки — English.
> Продакшн в будущем — на усмотрение заказчика (вероятно Unity); в Unity переносятся ассеты (GLB c анимациями), story JSON и дизайн-доки — код мока переписывается, это нормально для мока.

## Выбор стека (главное решение)

### Вариант A — Веб-прототип: Three.js + Vite (рекомендация Claude для МОКА)
- **Язык:** JavaScript/TypeScript
- Почему: Claude Code сильнее всего именно в вебе; мгновенный предпросмотр в браузере; заказчику отправляется просто **ссылка** — откроется на любом планшете/телефоне без установки (важно для NGO-питчей); модель GLB из Blender грузится нативно; touch из коробки
- Минусы: если потом продакшн в Unity/Godot — код не переносится (но дизайн, сценарий-JSON и вся 3D/анимация переносятся 1-в-1)

### Вариант B — Godot 4 + GDScript (рекомендация из GPT-инфо)
- Настоящий игровой движок, бесплатный, лёгкий; GDScript похож на Python; официальный pipeline Blender → glTF
- Минусы: нужно ставить и осваивать редактор; итерации медленнее, чем в браузере; шарить мок сложнее (нужен экспорт-билд, хотя есть и веб-экспорт)

### Вариант C — Unity (упоминается в клиентском доке)
- Плюс: совпадает с engineering spec заказчика
- Минусы: самый тяжёлый порог для дизайнера-соло; для мока избыточен. Логичен только если заказчик уже решил, что продакшн будет в Unity, и хочет мок сразу там

**С чем Claude не согласен в GPT-инфо:** только с тем, что Godot — безальтернативный выбор. Для *мока* веб быстрее и удобнее в демонстрации. Со всем остальным (vertical slice, JSON-сценарий, реалтайм-сцены вместо видео, фазы, «не открывай Blender первым») — согласен полностью.

## Архитектура (одинаковая идея для любого стека)

```
src/
├── core/            # game loop, состояния (EXPLORE / CHOICE / CINEMATIC / PAUSED)
├── player/          # управление Софи, движение, анимационные стейты
├── camera/          # FollowCamera + CinematicCamera (пресеты wide/close/OTS)
├── interaction/     # триггеры-зоны, пульсация подсветки
├── dialogue/        # панель выбора, реплики Софи, иконки
├── story/           # StoryEngine: читает story JSON, ведёт по сценам
├── safety/          # SafetyLayer: таймер бездействия, счётчик избеганий, интервенции Софи
├── audio/           # музыка-слои (calm/warm), мягкие UI-звуки
└── assets/          # sophie.glb, bruno.glb, environment.glb, icons, sounds
```

Ключевой принцип из клиентского дока и GPT (согласен): **сценарий не зашивается в код**. Психолог должен менять реплики и ветки, не трогая программу.

## Формат story JSON (сценарий = данные)

```json
{
  "mission": "bruno_missing_friend_feeling",
  "scenes": [
    {
      "id": "recognize_feeling",
      "type": "choice",
      "camera": "closeup_bruno",
      "prompt": { "voice": "sophie_what_feeling.mp3", "icon": "question" },
      "choices": [
        { "id": "lonely", "icon": "face_lonely", "next": "acknowledge",
          "sophie_line": "Yes. Bruno misses being close to friends." },
        { "id": "mad", "icon": "face_mad", "next": "recognize_feeling",
          "sophie_line": "Maybe a little frustrated... let's look again.", "redirect": true },
        { "id": "sleepy", "icon": "face_sleepy", "next": "recognize_feeling",
          "sophie_line": "Bruno looks droopy, but it's more about missing someone.", "redirect": true }
      ]
    },
    {
      "id": "acknowledge",
      "type": "cinematic",
      "camera": "wide",
      "actions": [
        { "actor": "bruno", "anim": "hand_to_chest" },
        { "actor": "sophie", "line": "It's okay to feel lonely sometimes." }
      ],
      "next": "choose_step",
      "bruno_state": "named"
    }
  ],
  "safety": { "idle_hint_sec": 10, "avoid_streak_soft_branch": 2 }
}
```

Разделять (по клиентскому доку): narrative outcome ≠ psychological interpretation. В JSON — только нарратив; интерпретации выборов — отдельный документ психолога, не в билде, ребёнку не показывается «правильно/неправильно».

## Пайплайн ассетов
Blender → export **GLB** (mesh + материалы + риг + все анимации в одном файле) → импорт в движок. Именованные анимации: `Idle, Walk, Run, Sit, Happy, Sad, Curious, Sniff, Bark, TailWag`.

## Локализация
Текста почти нет (иконки + озвучка), поэтому локализация = замена аудиофайлов + 2–3 строк. UA — базовая, EN — для питча. В story JSON реплики держать ключами (`sophie_line_id`), не строками.
