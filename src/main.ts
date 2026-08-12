import { Game } from './core/Game'
import { SophieController } from './player/SophieController'
import { FollowCamera } from './camera/FollowCamera'
import { InteractionSystem } from './interaction/InteractionSystem'
import { createBall, createBlocks, createBruno, createTree } from './interaction/Placeholders'
import { ChoicePanel } from './dialogue/ChoicePanel'
import { PauseOverlay } from './safety/PauseOverlay'
import demoScene from './story/demo_scene.json'

const container = document.getElementById('app')
if (!container) throw new Error('Missing #app container')

const game = new Game(container)

const controller = new SophieController(game)
const followCamera = new FollowCamera(game.camera, game.sophie)
const interaction = new InteractionSystem(game)
const choicePanel = new ChoicePanel(document.body)
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

interaction.add({
  id: 'bruno',
  object: bruno,
  triggerRadius: 3,
  onActivate: () => {
    game.states.transition('CHOICE')
    followCamera.focusOn(bruno)
    choicePanel.show(
      { promptIcon: demoScene.prompt.icon, choices: demoScene.choices },
      (choiceId) => {
        console.log(`[Choice] picked: ${choiceId}`)
        followCamera.focusOn(null)
        game.states.transition('EXPLORE')
      },
    )
  },
})

game.addUpdatable((dt) => controller.update(dt))
game.addUpdatable((dt, elapsed) => interaction.update(dt, elapsed))
game.addUpdatable((dt) => followCamera.update(dt))

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
    }
  }
}
window.game = game
window.sophieDebug = { controller, followCamera, interaction, choicePanel }
