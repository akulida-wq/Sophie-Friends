/**
 * Простой тёплый экран загрузки: портрет Софи, полоска прогресса.
 * Прогресс — по вехам (мир, Софи, Бруно, друзья) с мягкой доводкой,
 * чтобы полоска ползла плавно, а не прыгала.
 */
export class LoadingScreen {
  private readonly root: HTMLDivElement
  private readonly bar: HTMLDivElement
  private target = 0.04 // сразу чуть-чуть — «живая» полоска
  private shown = 0
  private totalWeight = 0
  private doneWeight = 0
  private raf: number | null = null
  private readonly shownAt = performance.now()

  constructor(container: HTMLElement) {
    this.root = document.createElement('div')
    this.root.className = 'loading-screen'
    const portrait = document.createElement('img')
    portrait.className = 'loading-screen__portrait'
    portrait.src = '/ui/portrait_sophie.png?v=2'
    portrait.alt = ''
    const title = document.createElement('div')
    title.className = 'loading-screen__title'
    title.textContent = 'Sophie & Friends'
    const track = document.createElement('div')
    track.className = 'loading-screen__track'
    this.bar = document.createElement('div')
    this.bar.className = 'loading-screen__bar'
    track.appendChild(this.bar)
    const hint = document.createElement('div')
    hint.className = 'loading-screen__hint'
    hint.textContent = 'getting the yard ready…'
    this.root.append(portrait, title, track, hint)
    container.appendChild(this.root)
    const tick = () => {
      // мягкая доводка к цели + лёгкое «дыхание» вперёд, пока грузится
      this.shown += (this.target - this.shown) * 0.08
      this.bar.style.width = `${Math.min(100, this.shown * 100)}%`
      this.raf = window.requestAnimationFrame(tick)
    }
    tick()
  }

  /** Учесть задачу загрузки; done двигает полоску пропорционально весу. */
  track<T>(promise: Promise<T>, weight: number): Promise<T> {
    this.totalWeight += weight
    return promise.finally(() => {
      this.doneWeight += weight
      this.target = Math.max(this.target, 0.04 + 0.96 * (this.doneWeight / this.totalWeight))
      if (this.doneWeight >= this.totalWeight) this.finish()
    })
  }

  private finish(): void {
    // полоска доезжает до конца и экран мягко тает (минимум 0.6с на экране)
    this.target = 1
    const wait = Math.max(0, 600 - (performance.now() - this.shownAt))
    window.setTimeout(() => {
      this.bar.style.width = '100%'
      this.root.classList.add('loading-screen--done')
      window.setTimeout(() => {
        if (this.raf !== null) window.cancelAnimationFrame(this.raf)
        this.root.remove()
      }, 800)
    }, wait + 250)
  }
}
