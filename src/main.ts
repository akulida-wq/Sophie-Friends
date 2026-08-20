import * as THREE from 'three'
import { Game } from './core/Game'
import { Mood } from './core/Mood'
import { Fireflies } from './core/Fireflies'
import { loadEnvironment, type PropId } from './core/Environment'
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
  createFriends,
  createTree,
} from './interaction/Placeholders'
import { BrunoView } from './interaction/BrunoView'
import { TapRipple } from './interaction/TapRipple'
import { ChoicePanel } from './dialogue/ChoicePanel'
import { SophieBubble } from './dialogue/SophieBubble'
import { TapCue } from './dialogue/TapCue'
import { FloatChip } from './dialogue/FloatChip'
import { IntroBanner } from './dialogue/IntroBanner'
import { RewardGlow } from './dialogue/RewardGlow'
import { PauseOverlay } from './safety/PauseOverlay'
import { SoundToggle } from './safety/SoundToggle'
import { SafetyLayer } from './safety/SafetyLayer'
import { StoryEngine } from './story/StoryEngine'
import type { StoryMission } from './story/types'
import brunoMission from './story/bruno.json'
import propsContent from './story/props.json'

// v-параметры обновлять при замене ассетов — сбрасывают кеш браузера.
const ASSET_SOPHIE = '/assets/sophie_meshy2.glb?v=3'
const ASSET_BRUNO = '/assets/bruno_meshy.glb?v=5'
const ASSET_ENV = '/assets/environment2.glb?v=11'

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
new PauseOverlay(document.body, game)
new SoundToggle(document.body)

controller.tapInterceptor = (raycaster) => interaction.tryActivate(raycaster)

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
brunoMarker.show(bruno, '💛', { height: 3.1 })
introBanner.show()
let namePlateShown = false

// --- Фоновые друзья (по спеку остаются заглушками), у песочницы ---
const friends = createFriends()
friends.position.set(5.2, 0, -8.6)
game.scene.add(friends)

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
const PROP_LINES = (propsContent as { prop_lines: Record<string, { line: string }> })
  .prop_lines

const PLACEHOLDER_PROPS: Record<PropId, [() => THREE.Group, [number, number, number]]> = {
  ball: [createBall, [3.5, 0, 1.5]],
  blocks: [createBlocks, [-4, 0, -2.5]],
  tree: [createTree, [5.5, 0, -6]],
  chalk: [createChalk, [1.5, 0, -4]],
}

const swayNodes: THREE.Object3D[] = []
const cloudNodes: THREE.Object3D[] = []

async function bootWorld(): Promise<void> {
  let props: Partial<Record<PropId, THREE.Object3D>> = {}
  try {
    const env = await loadEnvironment(ASSET_ENV)
    game.scene.getObjectByName('ground')?.removeFromParent() // серый пол долой
    game.scene.add(env.root)
    props = env.props
    for (const name of ['TreeDeco1', 'TreeDeco2', 'TreeDeco3', 'Tree',
                        'Bushes']) {
      const node = env.root.getObjectByName(name)
      if (node) swayNodes.push(node)
    }
    for (let i = 1; i <= 4; i++) {
      const cl = env.root.getObjectByName(`Cloud${i}`)
      if (cl) {
        cloudNodes.push(cl)
        // облака не должны тонуть в тумане дальнего плана
        cl.traverse((ch) => {
          const mesh = ch as THREE.Mesh
          if (mesh.isMesh) {
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
    interaction.add({
      id,
      object,
      triggerRadius: 2.5,
      onActivate: () => {
        const prop = PROP_LINES[id]
        if (prop && game.states.is('EXPLORE')) {
          sophieView.play('Curious')
          void bubble.say(prop.line)
        }
      },
    })
  }
  // друзья — тоже интерактив с мягкой заглушкой
  interaction.add({
    id: 'friends',
    object: friends,
    triggerRadius: 2.5,
    onActivate: () => {
      const prop = PROP_LINES['friends']
      if (prop && game.states.is('EXPLORE')) {
        sophieView.play('Happy')
        void bubble.say(prop.line)
      }
    },
  })
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
game.addUpdatable((dt, elapsed) => {
  // еле заметное покачивание зелени — медленный sin, не мигание
  swayNodes.forEach((n, i) => {
    n.rotation.z = Math.sin(elapsed * 0.4 + i * 1.7) * 0.012
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
