import { audio } from '../audio/AudioSystem'

/**
 * Кнопка вкл/выкл звука — всегда видна в верхнем углу рядом с паузой.
 * Выбор запоминается между сессиями (localStorage).
 */
export class SoundToggle {
  private readonly button: HTMLButtonElement

  constructor(container: HTMLElement) {
    this.button = document.createElement('button')
    this.button.className = 'sound-button'
    this.button.type = 'button'
    this.button.setAttribute('aria-label', 'Sound on/off')
    this.render(audio.isMuted)
    this.button.addEventListener('pointerdown', (e) => e.stopPropagation())
    this.button.addEventListener('click', () => {
      this.render(audio.toggleMuted())
    })
    container.appendChild(this.button)
  }

  private render(muted: boolean): void {
    this.button.textContent = muted ? '🔇' : '🔊'
  }
}
