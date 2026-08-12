/**
 * Sophie's speech bubble: soft fade in, holds, soft fade out.
 * Placeholder for voice-over — lines come from story JSON only.
 */
export class SophieBubble {
  private readonly root: HTMLDivElement
  private hideTimer: number | null = null

  constructor(container: HTMLElement) {
    this.root = document.createElement('div')
    this.root.className = 'sophie-bubble'
    container.appendChild(this.root)
  }

  say(line: string, holdMs = 2600): Promise<void> {
    return new Promise((resolve) => {
      if (this.hideTimer !== null) window.clearTimeout(this.hideTimer)
      this.root.textContent = `🐶 ${line}`
      this.root.classList.add('sophie-bubble--open')
      this.hideTimer = window.setTimeout(() => {
        this.root.classList.remove('sophie-bubble--open')
        this.hideTimer = null
        // Let the fade-out finish before resolving so scene pacing stays soft.
        window.setTimeout(resolve, 350)
      }, holdMs)
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
