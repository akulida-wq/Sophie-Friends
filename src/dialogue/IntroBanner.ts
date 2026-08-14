/**
 * Стартовая плашка-наведение от Софи: "Someone looks lonely today..."
 * Скрывается по тапу или сама через 6 секунд. Появляется один раз.
 */
export class IntroBanner {
  private readonly el: HTMLDivElement

  constructor(container: HTMLElement) {
    this.el = document.createElement('div')
    this.el.className = 'intro-banner'
    const avatar = document.createElement('span')
    avatar.className = 'sophie-avatar'
    avatar.textContent = '🐶'
    const text = document.createElement('span')
    text.className = 'intro-banner__text'
    text.textContent = "Someone looks lonely today. Let's go say hi!"
    this.el.append(avatar, text)
    this.el.addEventListener('click', () => this.hide())
    container.appendChild(this.el)
  }

  show(): void {
    this.el.classList.add('intro-banner--on')
    window.setTimeout(() => this.hide(), 6000)
  }

  hide(): void {
    this.el.classList.remove('intro-banner--on')
  }
}
