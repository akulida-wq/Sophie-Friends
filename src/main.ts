import { Game } from './core/Game'
import { SophieController } from './player/SophieController'
import { FollowCamera } from './camera/FollowCamera'

const container = document.getElementById('app')
if (!container) throw new Error('Missing #app container')

const game = new Game(container)

const controller = new SophieController(game)
const followCamera = new FollowCamera(game.camera, game.sophie)
game.addUpdatable((dt) => controller.update(dt))
game.addUpdatable((dt) => followCamera.update(dt))

game.start()

// Real transitions come from interaction / story systems in later tasks;
// exposed here so transitions can be tested from the browser console:
//   game.states.transition('PAUSED')
declare global {
  interface Window {
    game: Game
    sophieDebug: { controller: SophieController; followCamera: FollowCamera }
  }
}
window.game = game
window.sophieDebug = { controller, followCamera }
