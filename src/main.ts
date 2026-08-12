import { Game } from './core/Game'
import { SophieController } from './player/SophieController'
import { FollowCamera } from './camera/FollowCamera'
import { InteractionSystem } from './interaction/InteractionSystem'
import { createBall, createBlocks, createBruno, createTree } from './interaction/Placeholders'
import { ChoicePanel } from './dialogue/ChoicePanel'
import { SophieBubble } from './dialogue/SophieBubble'
import { PauseOverlay } from './safety/PauseOverlay'
import { SafetyLayer } from './safety/SafetyLayer'
import { StoryEngine } from './story/StoryEngine'
import type { StoryMission } from './story/types'
import brunoMission from './story/bruno.json'

const container = document.getElementById('app')
if (!container) throw new Error('Missing #app container')

const game = new Game(container)

const controller = new SophieController(game)
const followCamera = new FollowCamera(game.camera, game.sophie)
const interaction = new InteractionSystem(game)
const choicePanel = new ChoicePanel(document.body)
const bubble = new SophieBubble(document.body)
new PauseOverlay(document.body, game)

controller.tapInterceptor = (raycaster) => interaction.tryActivate(raycaster)

// --- Placeholder props and NPC (grey-box positions, GLB later) ---
const ball = createBall()
ball.position.set(3.5, 0, 1.5)
const blocks = createBlocks()
blocks.position.set(-4, 0, -2.5)
const tree = createTree()
tree.position.set(5.5, 0, -6)
const bruno = createBruno()
bruno.position.set(-3, 0, -8)
bruno.rotation.y = Math.PI / 6
game.scene.add(ball, blocks, tree, bruno)

for (const [id, object] of [
  ['ball', ball],
  ['blocks', blocks],
  ['tree', tree],
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
  game,
  followCamera,
  choicePanel,
  bubble,
  { resolve: (actorId) => (actorId === 'sophie' ? game.sophie : game.scene.getObjectByName(actorId) ?? null) },
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
game.addUpdatable((dt, elapsed) => interaction.update(dt, elapsed))
game.addUpdatable((dt) => followCamera.update(dt))
game.addUpdatable((dt) => safety.update(dt))

game.start()

// Debug handles for manual testing from the browser console.
declare global {
  interface Window {
    game: Game
    sophieDebug: {
      controller: SophieController
      followCamera: FollowCamera
      interaction: InteractionSystem
      choicePanel: ChoicePanel
      bubble: SophieBubble
      story: StoryEngine
      safety: SafetyLayer
    }
  }
}
window.game = game
window.sophieDebug = { controller, followCamera, interaction, choicePanel, bubble, story, safety }
