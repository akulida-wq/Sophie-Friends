/**
 * Мягкое тёплое сияние на награде (resolution): медленный радиальный
 * градиент, 0 -> 0.45 -> 0 за ~4.5 секунды. Никаких вспышек.
 */
export class RewardGlow {
  private readonly el: HTMLDivElement

  constructor(container: HTMLElement) {
    this.el = document.createElement('div')
    this.el.className = 'reward-glow'
    container.appendChild(this.el)
  }

  shine(): void {
    this.el.classList.remove('reward-glow--on')
    // перезапуск CSS-анимации
    void this.el.offsetWidth
    this.el.classList.add('reward-glow--on')
  }
}
