import { Game } from './core/Game'

const container = document.getElementById('app')
if (!container) throw new Error('Missing #app container')

const game = new Game(container)
game.start()

// Real transitions come from interaction / story systems in later tasks;
// exposed here so transitions can be tested from the browser console:
//   game.states.transition('PAUSED')
declare global {
  interface Window {
    game: Game
  }
}
window.game = game
