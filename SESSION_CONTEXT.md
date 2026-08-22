# SESSION_CONTEXT — Sophie & Friends (читать первым в новой сессии)

Обновлено: 2026-08-21. Этот файл — память чата с Артуром. Здесь всё, что
не выводится из кода: решения, грабли, конвейеры, статус.

## Что это
Vertical slice детской игры (4–9 лет, эмоциональная устойчивость,
Украина). Vite + Three.js + TS, порт 5185 (`.claude/launch.json` →
`sophie-dev`). Пितч-мок; ассеты и story JSON позже уедут в Unity.
CLAUDE.md — жёсткие правила (safety, контент только в src/story/*.json,
пауза/выход всегда, никакого fail-языка). Все фазы TASKS выполнены,
дальше — свободные итерации по фидбеку Артура.

## Рабочий цикл с Артуром
- Он генерит ассеты в Meshy AI (по моим промптам), кидает файлы в папку
  проекта или «3d meshed elements/». Файлы иногда НЕ докопируются
  (macOS textClipping/пустая папка) — всегда проверять и просить
  перекинуть.
- Я собираю всё Blender 5.0.1 CLI-скриптами из tools/blender/ и
  подключаю в движок. После КАЖДОГО блока — git commit + короткое резюме.
- Кэш ассетов сбрасывается версией в main.ts: `ASSET_* = '...glb?v=N'` —
  бампить при каждой пересборке GLB.
- Проверка: браузер-пейн (СКРЫТАЯ вкладка/пейн ЗАМОРАЖИВАЕТ rAF —
  игровой цикл стоит, cinematic-твины «висят» вечно: это НЕ баг игры,
  а артефакт замера! Перед плейтестом tabs_select и убедиться, что пейн
  реально виден; телепорт `window.game.sophie.position.set`,
  активация `window.sophieDebug.interaction.activate(id)`).

## Ассеты и скрипты (tools/blender/)
- `build_sophie_meshy2.py` → public/assets/sophie_meshy2.glb —
  РОДНОЙ квадрупед-риг Meshy (27 костей, армейчер scale 0.01 → вся
  математика в ЛОКАЛЬНЫХ единицах). Их Walking = Walk; Run — авторский
  галоп; остальные 9 клипов авторские (пробы осей). Sit/Sad — HOLD-позы
  (LoopOnce+clamp в SophieView). Ошейник+жетон rigid к chest (цвет-детект
  + growth; глаза тоже синие — резать по высоте!). tail_wag замыкает цикл
  (последний ключ = первому), иначе рывок.
- `build_bruno_meshy.py` → bruno_meshy.glb — риг Meshy biped (24 кости),
  12 их анимаций → 15 клипов игры (маппинг «спокойные для тихих сцен,
  яркие для пиков»); IdleSad = чистый Idle_3. Материал пересобран (basecolor
  + roughness .65 + эмиссив 0.07). Scale-треки из клипов ВЫРЕЗАТЬ.
- `build_environment2.py` → environment2.glb — весь мир одним GLB.
  Исходники в «3d meshed elements/» (переименованы понятно: house.glb,
  fence.glb, slide.glb, swings.glb, sandbox.glb, bench.glb, tree_new.glb,
  bush.glb, grass_tuft.glb, daisies.glb, cloud.glb, ball_soccer.glb,
  blocks_abc.glb, chalk_sticks.glb, gate.glb, pave_tile.glb, fountain.glb).
  clean_material = ЩАДЯЩИЙ ремонт (убрать эмиссив-дубль/спекуляр×2/alpha,
  родные карты оставить; base 2048, normal/MR 1024).

## ГРАБЛИ Blender/Meshy (повторяются!)
1. glTF-импорт даёт rotation_mode QUATERNION → rotation_euler МОЛЧА
   игнорится. Всегда obj.rotation_mode='XYZ' перед euler.
2. transform_apply и похожие ops в headless тихо фейлятся → data API
   (mesh.transform(matrix)).
3. Rest-позу риггованных моделей НЕ вращать — ломает пространство
   анимационных кривых при реэкспорте (модель взлетает). Ориентация — yaw
   параметром в SophieView/BrunoView.load(url, yaw).
4. Blender 5: Action.fcurves нет — кривые в act.layers→strips→channelbags.
5. Меши Meshy с анимациями таскают scale-треки (сжимают скелет до 0.68) и
   вертикаль Hips (топит в землю) — вырезать из клипов движения.
6. Коллапс-дециматизация РВЁТ плоские поверхности в дыры (плитка!).
   Для плоского: DISSOLVE (15°) + TRIANGULATE, без коллапса. Для
   органики коллапс ок (мелки 200k→16k норм).
7. Вьюер Meshy «Оживить» показывает модель страшной (плоский свет,
   пожатая текстура) — не паниковать, скачивать rigged GLB + pretty
   remeshed рядом; текстуру можно пересадить.
8. Сотни мелких объектов = сотни draw calls → merged_from() (bmesh) сливает
   размещения в 1 меш (забор/дорожка/тротуар). Но геометрия дублируется —
   исходник плитки должен быть лёгким.
9. NLA-треки подмешиваются под активный экшен при верификации — глушить
   (mute) перед пробами.
10. Экспорт текстур JPEG (quality 82) в env — режет файл в разы.

## Мир (планировка, three-координаты)
Квадратный двор ±15.8 (забор), газон ±16.6 кликабельный ('ground' —
raycast ходьбы ТОЛЬКО по нему; внешняя земля 'ground-outer' некликабельна
→ за двор не уйти). Улица СЛЕВА (запад): тротуар/бордюр/дорога с жёлтым
пунктиром, дома соседей, ворота+калитка (gate) на west z 0..4.5.
Дом СПРАВА (10.2, -3) rot -90 крыльцом на запад. Площадка север: горка
(-3,-11.6), качели (4.4,-12.6), песочница (8.5,-9.4) rot 0, друзья
(4.9,-8.6) полукругом, Бруно (-3,-8) rot π/6. Юг: скамейка (7.3,8.6) —
РЯДОМ с дорожкой col5 (восточнее), фонтан (-5.5,9.6). Дерево-декор (-8.6,-6.4).
ДОРОЖКИ: единая сетка клеток P=1.06, G0=0.87 (cell(k)=G0+k*P;
three z = cell(kz) напрямую). Ранны: главная (-16..13, rows 0..1), ветка
на площадку (cols 0..1, rows -13..-1), кольцо дома (col 13 / row -7 /
col 5), юг: col -6 → фонтан (rows 2..8), col 5 → лавка (rows 2..8),
поперечная запад→фонтан→лавка (cols -14..5, row 8; фонтан стоит на
мощёном пятачке перекрёстка), спуски к южному периметру col -6 и col 5
(rows 9..12), ПЕРИМЕТР вдоль забора (rows/cols -14 и 13).
Лавка rot -90. САД-КЛУМБА на юге: сетка 95 кустиков x∈[-4.4,5.2],
z∈[10.55,13.45], 4 тона (розовый/голубой/оранжевый/белый) — тонировка
Mix-MULTIPLY (build_environment2.py); трава там не сеется (AVOID_R),
коллайдер-прямоугольник — цветы не топчем.
Угловые деревья t1/t2 сдвинуты с периметра на (-12.8,-12.8)/(12.9,-12.9);
кусты (-6.2,-15.1), (-15.1,-2.0), (13.3,9.0).
Трава (инстансы, 3600) обходит ТЕ ЖЕ клетки (onTile в Environment.ts) —
менять раскладку = менять ОБА места. Друзья: ПОЛУКРУГ с просветом ~1.7м,
группа (4.9,-8.6): yellow(-1.6,0.45) yaw 1.25 (боком, лицом на восток),
red(0,-0.5) yaw 0.05 (центр, лицом к камере), pink(1.6,0.45) yaw -1.25
(боком). yaw 0 = мордой на юг/камеру. Жизнь: фиджеты Look/Chat раз в
20–35с у одного. ТРЮКОВ НЕТ (танец/бокс Meshy выглядят поломанными —
убраны по просьбе Артура; friend_*.glb v=2, red Idle=Idle_9, т.к. Idle_15
держит руку поднятой).

## Движок — что добавлено поверх фаз
- Очередь кликов: тап по объекту издалека → Софи идёт (goToInteract) →
  активация по прибытии; к Бруно — ВСЕГДА точка ПЕРЕД лицом (brunoFrontPoint,
  tapInterceptor перехватывает тап даже в радиусе: если Софи дальше 0.7 м от
  точки — сначала подбегает) + разворот к нему.
- Бруно в сценах успеха (recovery_*) — IdleOpen, без прыжка
  (Jump_with_Arms_Open Артур попросил убрать). Фонтан FOUNTAIN_VOLUME 0.35.
  sfx/drink.mp3 — вырезка 2.8с из dog_drinks.mp3 (окно 7.2–10.0с).
- Маркер над Бруно (talk-иконка) кликабелен (FloatChip.onTap).
- Коллизии двора: resolveYardCollisions (круги + прямоугольник дома +
  clamp забором) в Environment.ts; застревание >0.6с → мягкий стоп.
- TapRipple — кольцо в точке тапа.
- ExitButton (слева сверху, виден вне EXPLORE) → story.abort() обеих миссий.
- VideoOverlay: letterbox, /video/<id>.mp4, нет файла → тёплая заглушка 6с,
  тап = скип. Action {video: id} в story JSON.
- Вторая миссия memory.json (скамейка): сесть (Софи ОСТАЁТСЯ сидеть —
  HOLD) → выбор «peek/later» → видео → тёплый финал. camera: follow_sophie
  (иначе fallback целится в Бруно!).
- Гейт контента: пока brunoMet=false, пропсы говорят locked-подсказку
  «сначала Бруно». Калитка — тизер новой территории. Фонтан — Софи пьёт
  (Sniff 2.6s → TailWag + реплика). Дерево НЕ интерактив.
- BrunoView: цикличные оверлеи (танец) макс 7с; finish() сбрасывает
  оверлей (не танцует после миссии).
- Иконки: SVG-набор public/ui/icons/ (единый стиль), реестр
  dialogue/icons.ts ('img:'-пути), renderIcon(). Портреты
  public/ui/portrait_{sophie,bruno}.png — круглые кропы 2D-артов
  (make_art_portraits.py), друзья — кропы фото.
- Плашка диалога: низ по центру, Sims-стиль, портрет говорящего,
  время чтения от длины реплики. StoryEngine передаёт speaker по actor.
- Рендер: PCFSoft, IBL RoomEnvironment 0.45; газон Lambert (не бликует);
  небо 3-стопный градиент, туман 0xdcecf4 в цвет горизонта (Mood bg тоже);
  облака юзера на северном горизонте (далеко+крупно), без теней (тени
  давали «коричневые дыры»), подсветка emissive 0.42; кусты качаются
  по-отдельности (amp 0.005), деревья 0.012.
- FountainWater: капли-параболы (130), «дышащая» гладь, 3 кольца ряби.
- Аудио: music.mp3 лупом (mood ведёт громкость 0.55/0.68/0.8), фолбэк —
  процедурная шкатулка; голос /assets/voice/<id>.mp3 (33 файла на месте).
  audio.isVoicePlaying — гейт: клики по пропсам/калитке/фонтану молча
  игнорятся, пока звучит реплика (страховка 12с от зависшего плейбека);
  новая story-реплика снимает предыдущую. audio.sfx(name) →
  /assets/sfx/<name>.mp3 (нет файла — тишина); фонтан играет 'drink'.
  Фонтан: кулдаун 2 мин — повторный тап = fountain_full реплика.
- Минигра: StoryEngine.lastMinigameProp — сцена setback_recovery говорит
  вариант line_variants по выбранному предмету (мяч/кубики/мелки), проп-
  анимация чужого предмета скипается. end_menu to_hub_stub озвучен
  (s8_sophie_hub_soon). outcome_tree: Бруно НЕ садится (IdleSad).
- Мелки после миссии (brunoMet): chalk_activity в props.json — панель
  «Draw a sun / Another time» (state CHOICE), рисование: Sniff + sfx
  'chalk' → ChalkDrawing (процедурная меловая текстура-солнышко, плоский
  декаль на ближайшей плитке, НЕ на плитке самих мелков —
  nearestTileCenter(x,z,avoid)) → TailWag + реплика. Нарисовано — на всю
  сессию, повторный тап = «already». Exit отменяет (chalkGen).
- Реплика после минигры: s6_sophie_oops_{ball,blocks,chalk} от лица «мы»,
  без слова wobble (старая запись wobble_intro не используется).
- Портреты плашек: круглые кропы из 2D-артов Артура (Freinds fotos) —
  tools/blender/make_art_portraits.py; ссылки с ?v=2 (кеш-баст).

## Контент
- bruno.json — миссия Бруно (8 сцен + soft branch). Прояснено: гайд после
  outcome_*, интро в setback, реплики успеха; minigame camera follow_sophie.
- memory.json — скамейка/видео. props.json — реплики пропсов + locked +
  gate + fountain. VOICE_LINES.md — полный список для ElevenLabs
  (настройки: Multilingual v2, style ≤35%!). p_fountain_drink ещё не
  озвучен. Музыка: Twinkle Star Dreams.

## Стиль/промпты для Meshy (закреплено с Артуром)
Единый шаблон: одиночный объект, white background, 3/4, stylized 3D,
Pixar-качество, натуральная палитра (дерево/шалфей/небесный/терракота),
для персонажей + «glossy vinyl toy finish, NOT wet, rich saturated
colors». Мультивью: base-промпт (A-поза, руки от тела!) + «same character,
change NOTHING, [LEFT/RIGHT/BACK] view» в одном чате. Друзья: пары файлов
rigged + pretty.

## Статус / хвосты
- Друзья ГОТОВЫ: friend_{yellow,pink,red}.glb v=2 (build_friends.py из
  «Friends (riggs + animation)/*_merged.glb»), клипы Idle/Look/Chat, без
  трюков. Превью всех клипов Meshy: tools/blender/preview_friend_clips.py. Портреты
  public/ui/portrait_{yellow,red,pink}.png (круглые, для будущих плашек).
- Финал миссии: реплика s7_sophie_look_bruno («Look — Bruno is playing
  with everyone now!...»), end-menu: Keep exploring the yard / Play again /
  Visit another friend later.
- Голос Софи в ElevenLabs: Tilly (Bright, Spirited, Naive, Scrappy),
  Multilingual v2, speed 0.78, stability 65, similarity 85, style 25,
  speaker boost on (полностью — в VOICE_LINES.md). Голос Бруно — не
  зафиксирован.
- Звуки: /audio/fountain.mp3 — позиционный луп (AudioSystem.
  setFountainProximity по дистанции Софи: полная в 2 м, тишина за 13 м,
  setTargetAtTime 0.3с); sfx/drink.mp3 — вырезка 2.7с из
  «sound_garage-dog-drinking-water» (python: фейды+lowpass 5кГц+норм 0.62,
  mp3 через Blender VSE mixdown — tools/blender/encode_mp3.py; ffmpeg в системе
  НЕТ); sfx/chalk.mp3 от Артура. Голоса: все новые id на месте, кроме
  s7_sophie_look_bruno.
- Клавиша H (и русская Р) прячет HUD (body.hud-hidden, CSS в index.html) —
  для чистых скриншотов-референсов (видео в Higgsfield image-to-video).
- Ждём от Артура: public/video/memory1.mp4; голос s7_sophie_look_bruno.
- Дальше по плану Артура: интерфейс, логика, камера (после визуала).
- Старые ассеты сохранены (sophie.glb, sophie_meshy.glb, bruno.glb,
  environment.glb) — откат = смена ASSET_* в main.ts.
