import * as THREE from 'three'
import { Game } from './core/Game'
import { Mood } from './core/Mood'
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
import { ChoicePanel } from './dialogue/ChoicePanel'
import { SophieBubble } from './dialogue/SophieBubble'
import { TapCue } from './dialogue/TapCue'
import { RewardGlow } from './dialogue/RewardGlow'
import { PauseOverlay } from './safety/PauseOverlay'
import { SoundToggle } from './safety/SoundToggle'
import { SafetyLayer } from './safety/SafetyLayer'
import { StoryEngine } from './story/StoryEngine'
import type { StoryMission } from './story/types'
import brunoMission from './story/bruno.json'

// v-параметры обновлять при замене ассетов — сбрасывают кеш браузера.
const ASSET_SOPHIE = '/assets/sophie.glb?v=8'
const ASSET_BRUNO = '/assets/bruno.glb?v=3'
const ASSET_ENV = '/assets/environment.glb?v=1'

const container = document.getElementById('app')
if (!container) throw new Error('Missing #app container')

const game = new Game(container)

const controller = new SophieController(game)
const sophieView = new SophieView(game.sophie)
sophieView.load(ASSET_SOPHIE) // async; капсула остаётся при неудаче
controller.onAnimChange = (state) => sophieView.play(state)
const followCamera = new FollowCamera(game.camera, game.sophie)
const cinematicCamera = new CinematicCamera(game.camera)
const interaction = new InteractionSystem(game)
const choicePanel = new ChoicePanel(document.body)
const bubble = new SophieBubble(document.body)
const tapCue = new TapCue(document.body, game.camera)
const mood = new Mood(game.scene)
const rewardGlow = new RewardGlow(document.body)
new PauseOverlay(document.body, game)
new SoundToggle(document.body)

controller.tapInterceptor = (raycaster) => interaction.tryActivate(raycaster)

// --- Бруно: якорь-группа сразу (плейсхолдер), GLB подменяет содержимое ---
const bruno = createBruno()
bruno.position.set(-3, 0, -8)
bruno.rotation.y = Math.PI / 6
game.scene.add(bruno)
const brunoView = new BrunoView(bruno)
brunoView.load(ASSET_BRUNO)

// --- Фоновые друзья (по спеку остаются заглушками), у песочницы ---
const friends = createFriends()
friends.position.set(1.8, 0, -10.4)
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
  onActivate: () => story.start(),
})

// --- Мир: площадка из GLB; при неудаче — серый бокс-мир как раньше ---
const PLACEHOLDER_PROPS: Record<PropId, [() => THREE.Group, [number, number, number]]> = {
  ball: [createBall, [3.5, 0, 1.5]],
  blocks: [createBlocks, [-4, 0, -2.5]],
  tree: [createTree, [5.5, 0, -6]],
  chalk: [createChalk, [1.5, 0, -4]],
}

async function bootWorld(): Promise<void> {
  let props: Partial<Record<PropId, THREE.Object3D>> = {}
  try {
    const env = await loadEnvironment(ASSET_ENV)
    game.scene.getObjectByName('ground')?.removeFromParent() // серый пол долой
    game.scene.add(env.root)
    props = env.props
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
      onActivate: () => console.log(`[Interact] ${id} activated`),
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
game.addUpdatable(() => tapCue.update())
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
