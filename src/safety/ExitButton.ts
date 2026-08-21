/**
 * Кнопка «выйти из сцены»: видна только во время истории/катсцены.
 * Пользователь ВСЕГДА может мягко завершить взаимодействие (safety-правило).
 */
export class ExitButton {
  private readonly button: HTMLButtonElement

  constructor(container: HTMLElement, onExit: () => void) {
    this.button = document.createElement('button')
    this.button.className = 'exit-button'
    const img = document.createElement('img')
    img.src = '/ui/icons/away.svg'
    img.alt = 'leave scene'
    img.style.width = '62%'
    img.style.height = '62%'
    this.button.appendChild(img)
    this.button.addEventListener('click', onExit)
    container.appendChild(this.button)
  }

  setVisible(on: boolean): void {
    this.button.classList.toggle('exit-button--on', on)
  }
}
