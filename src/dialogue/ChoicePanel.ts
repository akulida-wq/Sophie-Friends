import { renderIcon } from './icons'
import { audio } from '../audio/AudioSystem'

export interface ChoiceOption {
  id: string
  icon: string
  label: string
}

export interface ChoicePanelContent {
  promptIcon?: string
  /** Optional question shown softly above the cards. */
  promptText?: string
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

    if (content.promptText) {
      const prompt = document.createElement('div')
      prompt.className = 'choice-panel__prompt'
      if (content.promptIcon) {
        const ic = document.createElement('span')
        ic.className = 'choice-panel__prompt-icon'
        renderIcon(ic, content.promptIcon)
        prompt.appendChild(ic)
      }
      const txt = document.createElement('span')
      txt.textContent = content.promptText
      prompt.appendChild(txt)
      this.root.appendChild(prompt)
    }

    const row = document.createElement('div')
    row.className = 'choice-panel__cards'
    this.root.appendChild(row)

    for (const choice of content.choices.slice(0, 3)) {
      const card = document.createElement('button')
      card.className = 'choice-card'
      card.type = 'button'

      const icon = document.createElement('span')
      icon.className = 'choice-card__icon'
      renderIcon(icon, choice.icon)

      const label = document.createElement('span')
      label.className = 'choice-card__label'
      label.textContent = choice.label

      card.append(icon, label)
      card.addEventListener('pointerdown', (e) => e.stopPropagation())
      card.addEventListener('click', () => this.pick(choice.id))
      row.appendChild(card)
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
    audio.ui('card')
    const handler = this.onPick
    this.hide()
    handler?.(id)
  }
}
