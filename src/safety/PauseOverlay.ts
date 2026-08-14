import { audio } from '../audio/AudioSystem'
import type { Game } from '../core/Game'
import type { GameState } from '../core/GameState'

/**
 * Pause/exit is always available (safety rule): a soft button in the top
 * corner, a calm full-screen veil while paused, tap anywhere to continue.
 * No confirm dialogs, no walls of text, no shame.
 */
export class PauseOverlay {
  private readonly button: HTMLButtonElement
  private readonly veil: HTMLDivElement
  private resumeState: GameState = 'EXPLORE'

  constructor(container: HTMLElement, private readonly game: Game) {
    this.button = document.createElement('button')
    this.button.className = 'pause-button'
    this.button.type = 'button'
    this.button.textContent = '⏸'
    this.button.setAttribute('aria-label', 'Pause')
    this.button.addEventListener('pointerdown', (e) => e.stopPropagation())
    this.button.addEventListener('click', () => this.pause())
    container.appendChild(this.button)

    this.veil = document.createElement('div')
    this.veil.className = 'pause-veil'
    const message = document.createElement('div')
    message.className = 'pause-veil__message'
    message.textContent = '🌙 Taking a little break. Tap to continue.'
    this.veil.appendChild(message)
    this.veil.addEventListener('click', () => this.resume())
    container.appendChild(this.veil)
  }

  private pause(): void {
    if (this.game.states.is('PAUSED')) return
    this.resumeState = this.game.states.state
    this.game.states.transition('PAUSED')
    this.veil.classList.add('pause-veil--open')
    audio.suspend()
  }

  private resume(): void {
    if (!this.game.states.is('PAUSED')) return
    this.veil.classList.remove('pause-veil--open')
    this.game.states.transition(this.resumeState)
    audio.resume()
  }
}
