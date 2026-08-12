export interface ChoiceOption {
  id: string
  icon: string
  label: string
}

export interface ChoicePanelContent {
  promptIcon?: string
  choices: ChoiceOption[]
}

/**
 * Large touch-card choice panel (Telltale-style, but with NO timer).
 * Max 3 cards, icon-first, min ~25% of screen height. Fades in softly.
 */
export class ChoicePanel {
  private readonly root: HTMLDivElement
  private onPick: ((id: string) => void) | null = null
  private openToken = 0

  constructor(container: HTMLElement) {
    this.root = document.createElement('div')
    this.root.className = 'choice-panel'
    container.appendChild(this.root)
  }

  get isOpen(): boolean {
    return this.root.classList.contains('choice-panel--open')
  }

  show(content: ChoicePanelContent, onPick: (id: string) => void): void {
    this.onPick = onPick
    this.root.innerHTML = ''

    for (const choice of content.choices.slice(0, 3)) {
      const card = document.createElement('button')
      card.className = 'choice-card'
      card.type = 'button'

      const icon = document.createElement('span')
      icon.className = 'choice-card__icon'
      icon.textContent = choice.icon

      const label = document.createElement('span')
      label.className = 'choice-card__label'
      label.textContent = choice.label

      card.append(icon, label)
      card.addEventListener('pointerdown', (e) => e.stopPropagation())
      card.addEventListener('click', () => this.pick(choice.id))
      this.root.appendChild(card)
    }

    // Double rAF so the browser paints the hidden state before the
    // transition starts — a soft fade/slide, never a pop. The token guards
    // against a stale rAF re-opening the panel after hide().
    const token = ++this.openToken
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        if (token === this.openToken) this.root.classList.add('choice-panel--open')
      })
    })
  }

  hide(): void {
    this.openToken++
    this.onPick = null
    this.root.classList.remove('choice-panel--open')
  }

  private pick(id: string): void {
    const handler = this.onPick
    this.hide()
    handler?.(id)
  }
}
