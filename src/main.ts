import * as THREE from 'three'
import { Game } from './core/Game'
import { Mood } from './core/Mood'
import { Fireflies } from './core/Fireflies'
import { FountainWater } from './core/FountainWater'
import { loadEnvironment, nearestTileCenter, type PropId } from './core/Environment'
import { SophieController } from './player/SophieController'
import { SophieView } from './player/SophieView'
import { FollowCamera } from './camera/FollowCamera'
import { CinematicCamera } from './camera/CinematicCamera'
import { InteractionSystem } from './interaction/InteractionSystem'
import {
  createBall,
  createBlocks,
  createBruno,
  createChalk,
  createTree,
} from './interaction/Placeholders'
import { BrunoView } from './interaction/BrunoView'
import { FriendView } from './interaction/FriendView'
import { ChalkDrawing } from './interaction/ChalkDrawing'
import { TapRipple } from './interaction/TapRipple'
import { VideoOverlay } from './dialogue/VideoOverlay'
import { ExitButton } from './safety/ExitButton'
import { ChoicePanel } from './dialogue/ChoicePanel'
import { SophieBubble } from './dialogue/SophieBubble'
import { TapCue } from './dialogue/TapCue'
import { FloatChip } from './dialogue/FloatChip'
import { IntroBanner } from './dialogue/IntroBanner'
import { RewardGlow } from './dialogue/RewardGlow'
import { PauseOverlay } from './safety/PauseOverlay'
import { SoundToggle } from './safety/SoundToggle'
import { SafetyLayer } from './safety/SafetyLayer'
import { audio } from './audio/AudioSystem'
import { iconFor } from './dialogue/icons'
import { StoryEngine } from './story/StoryEngine'
import type { StoryMission } from './story/types'
import brunoMission from './story/bruno.json'
import propsContent from './story/props.json'
import memoryMission from './story/memory.json'

// v-параметры обновлять при замене ассетов — сбрасывают кеш браузера.
const ASSET_SOPHIE = '/assets/sophie_meshy2.glb?v=5'
const ASSET_BRUNO = '/assets/bruno_meshy.glb?v=5'
const ASSET_ENV = '/assets/environment2.glb?v=19'

const container = document.getElementById('app')
if (!container) throw new Error('Missing #app container')

const game = new Game(container)

const controller = new SophieController(game)
const sophieView = new SophieView(game.sophie)
sophieView.load(ASSET_SOPHIE, 0) // async; капсула остаётся при неудаче
controller.onAnimChange = (state) => sophieView.play(state)
const followCamera = new FollowCamera(game.camera, game.sophie)
const cinematicCamera = new CinematicCamera(game.camera)
const interaction = new InteractionSystem(game)
const choicePanel = new ChoicePanel(document.body)
const bubble = new SophieBubble(document.body)
const tapCue = new TapCue(document.body, game.camera)
const mood = new Mood(game.scene)
const fireflies = new Fireflies(game.scene)
mood.onTempChange = (temp) => fireflies.setActive(temp === 'warm')
const rewardGlow = new RewardGlow(document.body)
const tapRipple = new TapRipple(game.scene)
controller.onMoveTarget = (p) => tapRipple.show(p)
const videoOverlay = new VideoOverlay(document.body)
new PauseOverlay(document.body, game)
new SoundToggle(document.body)

controller.tapInterceptor = (raycaster) => interaction.tryActivate(raycaster)
// Точка «напротив Бруно»: подходим к его лицу, с какой бы стороны ни шли
function brunoFrontPoint(): THREE.Vector3 {
  const p = new THREE.Vector3()
  bruno.getWorldPosition(p)
  p.y = 0
  const dir = new THREE.Vector3(Math.sin(bruno.rotation.y), 0, Math.cos(bruno.rotation.y))
  return p.addScaledVector(dir, 1.7)
}

controller.findFarTap = (rc) => {
  const item = interaction.findTapped(rc)
  if (!item) return null
  if (item.id === 'bruno') {
    return { id: 'bruno', point: brunoFrontPoint(), radius: 0.2 }
  }
  const point = new THREE.Vector3()
  item.object.getWorldPosition(point)
  point.y = 0
  return { id: item.id, point, radius: item.triggerRadius }
}
controller.onArrivedAtInteract = (id) => {
  if (id === 'bruno') {
    // повернуться лицом к Бруно перед разговором
    const bp = new THREE.Vector3()
    bruno.getWorldPosition(bp)
    const s = game.sophie.position
    game.sophie.rotation.y = Math.atan2(bp.x - s.x, bp.z - s.z)
  }
  interaction.activate(id)
}

// --- Бруно: якорь-группа сразу (плейсхолдер), GLB подменяет содержимое ---
const bruno = createBruno()
bruno.position.set(-3, 0, -8)
bruno.rotation.y = Math.PI / 6
game.scene.add(bruno)
const brunoView = new BrunoView(bruno)
void brunoView.load(ASSET_BRUNO, 0).then((ok) => {
  // glow должен светить GLB-модель, а не снятый плейсхолдер
  if (ok) interaction.invalidate('bruno')
})

// --- Онбординг: маркер над Бруно + стартовая плашка от Софи ---
const brunoMarker = new FloatChip(document.body, game.camera, 'marker')
const namePlate = new FloatChip(document.body, game.camera, 'name')
const introBanner = new IntroBanner(document.body)
brunoMarker.onTap = () => controller.goToInteract('bruno', brunoFrontPoint(), 0.2)
brunoMarker.show(bruno, 'img:/ui/icons/talk.svg', { height: 3.1 })
introBanner.show()
let namePlateShown = false

// --- Друзья-монстрики у песочницы: Idle + изредка Look/Chat, трюки по
// расписанию (раз в минуту, по очереди: жёлтый танцует, красный боксирует)
const friends = new THREE.Group()
friends.name = 'friends'
friends.position.set(4.6, 0, -8.6)
game.scene.add(friends)

// полукруг, раскрытый к камере (юг): все трое видны, чуть повёрнуты к центру
const FRIEND_SPECS = [
  { id: 'yellow', url: '/assets/friend_yellow.glb?v=1', offset: [-1.15, 0.15], yaw: 0.35, height: 2.0 },
  { id: 'pink', url: '/assets/friend_pink.glb?v=1', offset: [0.0, 0.75], yaw: 0, height: 1.8 },
  { id: 'red', url: '/assets/friend_red.glb?v=1', offset: [1.15, 0.1], yaw: -0.35, height: 2.05 },
] as const
const friendViews: FriendView[] = []
const friendLoads: Promise<boolean>[] = []
for (const spec of FRIEND_SPECS) {
  const anchor = new THREE.Group()
  anchor.name = `friend-${spec.id}`
  anchor.position.set(spec.offset[0], 0, spec.offset[1])
  friends.add(anchor)
  const view = new FriendView(anchor, spec.height)
  friendLoads.push(view.load(spec.url, spec.yaw))
  friendViews.push(view)
}
// свечение интерактива должно светить настоящие модели, не пустую группу
void Promise.all(friendLoads).then(() => interaction.invalidate('friends'))
// живость: каждый изредка озирается/болтает (вразнобой)
let friendFidgetAt = 14
// трюки: раз в минуту, по очереди (0 = жёлтый танец, 2 = красный бокс)
let trickAt = 25
let trickTurn = 0

// --- Story: mission JSON drives everything after this point ---
const story = new StoryEngine(
  {
    game,
    followCamera,
    cinematicCamera,
    choicePanel,
    bubble,
    tapCue,
    interaction,
    brunoView,
    mood,
    rewardGlow,
    videoOverlay,
    actors: {
      resolve: (actorId) =>
        actorId === 'sophie' ? game.sophie : game.scene.getObjectByName(actorId) ?? null,
    },
    playActorAnim: (actorId, anim) =>
      actorId === 'sophie'
        ? sophieView.play(anim)
        : actorId === 'bruno'
          ? brunoView.play(anim)
          : false,
  },
  brunoMission as StoryMission,
)

// --- Вторая миссия: «Солнечное воспоминание» у скамейки (видео-вставка) ---
const memoryStory = new StoryEngine(
  {
    game,
    followCamera,
    cinematicCamera,
    choicePanel,
    bubble,
    tapCue,
    interaction,
    brunoView,
    mood,
    rewardGlow,
    videoOverlay,
    actors: {
      resolve: (actorId) =>
        actorId === 'sophie' ? game.sophie : game.scene.getObjectByName(actorId) ?? null,
    },
    playActorAnim: (actorId, anim) =>
      actorId === 'sophie' ? sophieView.play(anim) : false,
  },
  memoryMission as StoryMission,
)

// гейт: пока не познакомились с Бруно, остальной интерактив мягко
// подсказывает первый шаг
let brunoMet = false
story.onFinished = () => {
  brunoMet = true
}

// выход из сцены доступен всегда
const exitButton = new ExitButton(document.body, () => {
  story.abort()
  memoryStory.abort()
  cancelChalkActivity()
})
game.addUpdatable(() => exitButton.setVisible(!game.states.is('EXPLORE')))

const safety = new SafetyLayer(game, interaction, bubble, story)
controller.onInput = () => safety.notifyActivity()

interaction.add({
  id: 'bruno',
  object: bruno,
  triggerRadius: 3,
  onActivate: () => {
    brunoMarker.hide() // наведение выполнило свою задачу
    introBanner.hide()
    story.start()
  },
})

// --- Мир: площадка из GLB; при неудаче — серый бокс-мир как раньше ---
type Line = { line: string; voice?: string }
const PROPS_CONTENT = propsContent as {
  prop_lines: Record<string, Line>
  locked: Line
  chalk_activity: {
    prompt: Line & { icon?: string }
    choices: { id: string; icon: string; label: string }[]
    later: Line
    drawn: Line
    already: Line
  }
}
const PROP_LINES = PROPS_CONTENT.prop_lines

// --- Мелки после миссии: выбор «нарисовать / в другой раз», солнышко на
// ближайшей плитке; нарисовано — на всю сессию (без таймера)
let chalkDrawing: ChalkDrawing | null = null
let chalkGen = 0 // выход/отмена обесценивает отложенные шаги
let chalkBusy = false

function sayLine(l: Line, anim: string): void {
  sophieView.play(anim)
  audio.voice(l.voice)
  void bubble.say(l.line)
}

function cancelChalkActivity(): void {
  if (!chalkBusy) return
  chalkGen++
  chalkBusy = false
  choicePanel.hide()
  if (!game.states.is('EXPLORE')) game.states.transition('EXPLORE')
  sophieView.play('Idle')
}

function chalkActivity(): void {
  const act = PROPS_CONTENT.chalk_activity
  if (chalkDrawing?.drawn) return sayLine(act.already, 'Happy')
  chalkBusy = true
  const gen = ++chalkGen
  game.states.transition('CHOICE')
  sophieView.play('Curious')
  audio.voice(act.prompt.voice)
  choicePanel.show(
    {
      promptIcon: iconFor(act.prompt.icon),
      promptText: act.prompt.line,
      choices: act.choices.slice(0, 3).map((c) => ({ id: c.id, icon: iconFor(c.icon), label: c.label })),
    },
    (pick) => {
      if (gen !== chalkGen) return
      choicePanel.hide()
      if (pick === 'draw') return drawChalkSun(act, gen)
      chalkBusy = false
      game.states.transition('EXPLORE')
      sayLine(act.later, 'Idle')
    },
  )
}

function drawChalkSun(act: typeof PROPS_CONTENT.chalk_activity, gen: number): void {
  game.states.transition('CINEMATIC') // кнопка выхода видна, ходьба на паузе
  const sp = game.sophie.position
  // не на плитке, где лежат сами мелки — рисунок должен быть виден
  const chalkNode = game.scene.getObjectByName('Chalk')
  const chalkAt = chalkNode ? chalkNode.getWorldPosition(new THREE.Vector3()) : undefined
  const tile = nearestTileCenter(sp.x, sp.z, chalkAt) ?? new THREE.Vector3(sp.x, 0, sp.z + 1)
  // мордой к плитке, рисунок — на ней (чуть выше плиты)
  game.sophie.rotation.y = Math.atan2(tile.x - sp.x, tile.z - sp.z)
  chalkDrawing = new ChalkDrawing(game.scene, tile.clone().setY(0.075))
  sophieView.play('Sniff') // носом к земле — «рисует»
  audio.sfx('chalk', 0.4)
  window.setTimeout(() => {
    if (gen === chalkGen) chalkDrawing?.reveal()
  }, 1400)
  window.setTimeout(() => {
    if (gen !== chalkGen) return
    sophieView.play('TailWag')
    audio.voice(act.drawn.voice)
    void bubble.say(act.drawn.line).then(() => {
      if (gen !== chalkGen) return
      chalkBusy = false
      game.states.transition('EXPLORE')
      sophieView.play('Idle')
    })
  }, 3200)
}

function propActivated(id: string): void {
  if (!game.states.is('EXPLORE')) return
  // пока звучит предыдущая реплика — повторный тап молча ждёт её конца
  if (audio.isVoicePlaying) return
  if (!brunoMet) {
    // подсказываем первый шаг и подсвечиваем Бруно
    sophieView.play('Curious')
    audio.voice(PROPS_CONTENT.locked.voice)
    void bubble.say(PROPS_CONTENT.locked.line)
    brunoMarker.show(bruno, 'img:/ui/icons/talk.svg', { height: 3.1, autohideMs: 4000 })
    return
  }
  if (id === 'chalk') return chalkActivity()
  const prop = PROP_LINES[id]
  if (prop) {
    sophieView.play(id === 'friends' ? 'Happy' : 'Curious')
    audio.voice(prop.voice)
    void bubble.say(prop.line)
  }
}

const PLACEHOLDER_PROPS: Record<PropId, [() => THREE.Group, [number, number, number]]> = {
  ball: [createBall, [3.5, 0, 1.5]],
  blocks: [createBlocks, [-4, 0, -2.5]],
  tree: [createTree, [5.5, 0, -6]],
  chalk: [createChalk, [1.5, 0, -4]],
}

const swayNodes: { node: THREE.Object3D; amp: number }[] = []
const cloudNodes: THREE.Object3D[] = []
let fountainWater: FountainWater | null = null

async function bootWorld(): Promise<void> {
  let props: Partial<Record<PropId, THREE.Object3D>> = {}
  try {
    const env = await loadEnvironment(ASSET_ENV)
    game.scene.getObjectByName('ground')?.removeFromParent() // серый пол долой
    game.scene.add(env.root)
    props = env.props
    for (const name of ['TreeDeco1', 'TreeDeco2', 'TreeDeco3', 'Tree']) {
      const node = env.root.getObjectByName(name)
      if (node) swayNodes.push({ node, amp: 0.012 })
    }
    // кусты качаются каждый вокруг СВОЕЙ базы (группой их «подбрасывало»)
    const bushes = env.root.getObjectByName('Bushes')
    bushes?.children.forEach((bush) => swayNodes.push({ node: bush, amp: 0.005 }))
    // живая вода фонтана
    const fountainNode = env.root.getObjectByName('Fountain')
    if (fountainNode) fountainWater = new FountainWater(game.scene, fountainNode)
    for (let i = 1; i <= 4; i++) {
      const cl = env.root.getObjectByName(`Cloud${i}`)
      if (cl) {
        cloudNodes.push(cl)
        // облака не должны тонуть в тумане дальнего плана
        cl.traverse((ch) => {
          const mesh = ch as THREE.Mesh
          if (mesh.isMesh) {
            mesh.castShadow = false // тени облаков = «коричневые дыры» на газоне
            const m = mesh.material as THREE.MeshStandardMaterial
            m.fog = false
            // облако не должно сереть с теневой стороны
            m.emissive = new THREE.Color(0xffffff)
            m.emissiveIntensity = 0.42
          }
        })
      }
    }
  } catch (err) {
    console.warn('[Environment] failed — falling back to grey box world', err)
  }
  for (const [id, [factory, pos]] of Object.entries(PLACEHOLDER_PROPS) as [
    PropId,
    [() => THREE.Group, [number, number, number]],
  ][]) {
    let object = props[id]
    if (!object) {
      const placeholder = factory()
      placeholder.position.set(...pos)
      game.scene.add(placeholder)
      object = placeholder
    }
    if (id === 'tree') continue // дерево — декор, не интерактив
    interaction.add({
      id,
      object,
      triggerRadius: 2.5,
      onActivate: () => propActivated(id),
    })
  }
  // друзья — интерактив с мягкой заглушкой
  interaction.add({
    id: 'friends',
    object: friends,
    triggerRadius: 2.5,
    onActivate: () => propActivated('friends'),
  })
  // калитка: тизер новой территории
  const gateNode = game.scene.getObjectByName('Gate')
  if (gateNode) {
    interaction.add({
      id: 'gate',
      object: gateNode,
      triggerRadius: 2.6,
      onActivate: () => {
        if (!game.states.is('EXPLORE') || audio.isVoicePlaying) return
        const prop = PROP_LINES['gate']
        if (prop) {
          sophieView.play('Curious')
          audio.voice(prop.voice)
          void bubble.say(prop.line)
        }
      },
    })
  }
  // фонтан: Софи подходит и пьёт воду (повторно — не раньше чем через 2 мин)
  const DRINK_COOLDOWN_MS = 120_000
  let lastDrinkAt = -DRINK_COOLDOWN_MS
  const fountainInteractNode = game.scene.getObjectByName('Fountain')
  if (fountainInteractNode) {
    interaction.add({
      id: 'fountain',
      object: fountainInteractNode,
      triggerRadius: 2.9,
      onActivate: () => {
        if (!game.states.is('EXPLORE') || audio.isVoicePlaying) return
        // мордой к воде
        const fp = new THREE.Vector3()
        fountainInteractNode.getWorldPosition(fp)
        const sp = game.sophie.position
        game.sophie.rotation.y = Math.atan2(fp.x - sp.x, fp.z - sp.z)
        // жажда утолена надолго: повторный тап — мягкий отказ без анимации питья
        if (performance.now() - lastDrinkAt < DRINK_COOLDOWN_MS) {
          sophieView.play('Happy')
          const prop = PROP_LINES['fountain_full']
          if (prop) {
            audio.voice(prop.voice)
            void bubble.say(prop.line)
          }
          return
        }
        lastDrinkAt = performance.now()
        // «пьёт»: нос к воде (Sniff) + журчание, потом довольное виляние
        sophieView.play('Sniff')
        audio.sfx('drink', 0.45)
        window.setTimeout(() => {
          if (game.states.is('EXPLORE')) {
            if (!controller.isMoving) sophieView.play('TailWag')
            const prop = PROP_LINES['fountain']
            if (prop) {
              audio.voice(prop.voice)
              void bubble.say(prop.line)
            }
          }
        }, 2600)
        window.setTimeout(() => {
          if (!controller.isMoving && game.states.is('EXPLORE')) sophieView.play('Idle')
        }, 5400)
      },
    })
  }
  // скамейка запускает миссию-воспоминание (доступна сразу)
  const benchNode = game.scene.getObjectByName('Bench')
  if (benchNode) {
    interaction.add({
      id: 'bench',
      object: benchNode,
      triggerRadius: 2.6,
      onActivate: () => {
        if (game.states.is('EXPLORE')) memoryStory.start()
      },
    })
  }
}

void bootWorld()

game.addUpdatable((dt) => controller.update(dt))
game.addUpdatable((dt) => sophieView.update(dt))
game.addUpdatable((dt, elapsed) => interaction.update(dt, elapsed))
game.addUpdatable((dt) => followCamera.update(dt))
game.addUpdatable((dt) => cinematicCamera.update(dt))
game.addUpdatable((dt) => brunoView.update(dt))
game.addUpdatable((dt) => mood.update(dt))
game.addUpdatable((dt, elapsed) => fireflies.update(dt, elapsed))
game.addUpdatable((dt, elapsed) => fountainWater?.update(dt, elapsed))
game.addUpdatable((dt) => friendViews.forEach((f) => f.update(dt)))
game.addUpdatable((dt) => chalkDrawing?.update(dt))
game.addUpdatable((_dt, elapsed) => {
  if (elapsed >= friendFidgetAt) {
    // случайный друг коротко оживает — Look или Chat
    const f = friendViews[Math.floor(elapsed * 7.13) % friendViews.length]
    f.playOnce(Math.floor(elapsed * 3.7) % 2 === 0 ? 'Look' : 'Chat')
    friendFidgetAt = elapsed + 9 + (elapsed * 5.3) % 8
  }
  if (elapsed >= trickAt) {
    // показ раз в минуту, строго по очереди: жёлтый -> красный -> жёлтый...
    const performer = trickTurn % 2 === 0 ? friendViews[0] : friendViews[2]
    if (performer?.hasClip('Trick')) performer.playOnce('Trick')
    trickTurn++
    trickAt = elapsed + 60
  }
})
game.addUpdatable((dt, elapsed) => {
  // еле заметное покачивание зелени — медленный sin, не мигание
  swayNodes.forEach(({ node, amp }, i) => {
    node.rotation.z = Math.sin(elapsed * 0.4 + i * 1.7) * amp
  })
  // облака: очень медленный дрейф с заворотом по кругу
  cloudNodes.forEach((n, i) => {
    n.position.x += dt * (0.25 + i * 0.08)
    if (n.position.x > 42) n.position.x = -42
  })
})
game.addUpdatable(() => tapCue.update())
game.addUpdatable(() => {
  brunoMarker.update()
  namePlate.update()
  if (!namePlateShown && game.sophie.position.distanceTo(bruno.position) < 4.2) {
    namePlateShown = true
    namePlate.show(bruno, 'Bruno', { height: 2.75, autohideMs: 3500 })
  }
})
game.addUpdatable((dt) => tapRipple.update(dt))
game.addUpdatable((dt) => safety.update(dt))

game.start()

// Debug handles for manual testing from the browser console.
declare global {
  interface Window {
    game: Game
    sophieDebug: {
      controller: SophieController
      sophieView: SophieView
      followCamera: FollowCamera
      cinematicCamera: CinematicCamera
      interaction: InteractionSystem
      choicePanel: ChoicePanel
      bubble: SophieBubble
      tapCue: TapCue
      brunoView: BrunoView
      mood: Mood
      story: StoryEngine
      safety: SafetyLayer
    }
  }
}
window.game = game
window.sophieDebug = {
  controller,
  sophieView,
  followCamera,
  cinematicCamera,
  interaction,
  choicePanel,
  bubble,
  tapCue,
  brunoView,
  mood,
  story,
  safety,
}
