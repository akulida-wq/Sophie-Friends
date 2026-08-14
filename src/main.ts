import { Game } from './core/Game'
import { Mood } from './core/Mood'
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
import { PauseOverlay } from './safety/PauseOverlay'
import { SafetyLayer } from './safety/SafetyLayer'
import { StoryEngine } from './story/StoryEngine'
import type { StoryMission } from './story/types'
import brunoMission from './story/bruno.json'

const container = document.getElementById('app')
if (!container) throw new Error('Missing #app container')

const game = new Game(container)

const controller = new SophieController(game)
const sophieView = new SophieView(game.sophie)
// v-параметр обновлять при замене ассета — сбрасывает кеш браузера.
sophieView.load('/assets/sophie.glb?v=7') // async; capsule stays if it fails
controller.onAnimChange = (state) => sophieView.play(state)
const followCamera = new FollowCamera(game.camera, game.sophie)
const cinematicCamera = new CinematicCamera(game.camera)
const interaction = new InteractionSystem(game)
const choicePanel = new ChoicePanel(document.body)
const bubble = new SophieBubble(document.body)
const tapCue = new TapCue(document.body, game.camera)
const mood = new Mood(game.scene)
new PauseOverlay(document.body, game)

controller.tapInterceptor = (raycaster) => interaction.tryActivate(raycaster)

// --- Placeholder props, NPC and friends (grey-box, GLB in Tasks 7-8) ---
const ball = createBall()
ball.position.set(3.5, 0, 1.5)
const blocks = createBlocks()
blocks.position.set(-4, 0, -2.5)
const tree = createTree()
tree.position.set(5.5, 0, -6)
const chalk = createChalk()
chalk.position.set(1.5, 0, -4)
const bruno = createBruno()
bruno.position.set(-3, 0, -8)
bruno.rotation.y = Math.PI / 6
const friends = createFriends()
friends.position.set(4, 0, -12)
game.scene.add(ball, blocks, tree, chalk, bruno, friends)

const brunoView = new BrunoView(bruno)

for (const [id, object] of [
  ['ball', ball],
  ['blocks', blocks],
  ['tree', tree],
  ['chalk', chalk],
] as const) {
  interaction.add({
    id,
    object,
    triggerRadius: 2.5,
    onActivate: () => console.log(`[Interact] ${id} activated`),
  })
}

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
    actors: {
      resolve: (actorId) =>
        actorId === 'sophie' ? game.sophie : game.scene.getObjectByName(actorId) ?? null,
    },
    playActorAnim: (actorId, anim) => (actorId === 'sophie' ? sophieView.play(anim) : false),
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
