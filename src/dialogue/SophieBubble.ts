export type Speaker = 'sophie' | 'bruno'

const PORTRAITS: Record<Speaker, string> = {
  sophie: '/ui/portrait_sophie.png',
  bruno: '/ui/portrait_bruno.png',
}

/**
 * Диалоговая плашка: портрет говорящего в кружке, текст по центру,
 * время показа зависит от длины реплики. Реплики — только из story JSON.
 */
export class SophieBubble {
  private readonly root: HTMLDivElement
  private hideTimer: number | null = null

  private readonly textEl: HTMLSpanElement
  private readonly portrait: HTMLImageElement

  constructor(container: HTMLElement) {
    this.root = document.createElement('div')
    this.root.className = 'sophie-bubble'
    const avatar = document.createElement('span')
    avatar.className = 'sophie-avatar'
    this.portrait = document.createElement('img')
    this.portrait.src = PORTRAITS.sophie
    this.portrait.alt = ''
    avatar.appendChild(this.portrait)
    this.textEl = document.createElement('span')
    this.textEl.className = 'sophie-bubble__text'
    this.root.append(avatar, this.textEl)
    container.appendChild(this.root)
  }

  say(line: string, holdMs?: number, speaker: Speaker = 'sophie'): Promise<void> {
    // время на прочтение: спокойный темп, зависит от длины строки
    const hold = holdMs ?? Math.min(8000, Math.max(3400, 1600 + line.length * 55))
    return new Promise((resolve) => {
      if (this.hideTimer !== null) window.clearTimeout(this.hideTimer)
      this.portrait.src = PORTRAITS[speaker]
      this.textEl.textContent = line
      this.root.classList.add('sophie-bubble--open')
      this.hideTimer = window.setTimeout(() => {
        this.root.classList.remove('sophie-bubble--open')
        this.hideTimer = null
        // Let the fade-out finish before resolving so scene pacing stays soft.
        window.setTimeout(resolve, 350)
      }, hold)
    })
  }

  hideNow(): void {
    if (this.hideTimer !== null) {
      window.clearTimeout(this.hideTimer)
      this.hideTimer = null
    }
    this.root.classList.remove('sophie-bubble--open')
  }
}
