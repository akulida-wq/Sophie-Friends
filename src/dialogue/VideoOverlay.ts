/**
 * Кино-вставка (как заставки в GTA, только мягко): чёрный letterbox,
 * видео из /video/<id>.mp4. Если файла нет — тёплая плашка-заглушка.
 * Тап в любой момент завершает вставку (правило: выход всегда доступен).
 */
export class VideoOverlay {
  private readonly root: HTMLDivElement
  private readonly video: HTMLVideoElement
  private readonly placeholder: HTMLDivElement
  private finish: (() => void) | null = null
  private timer: number | null = null

  constructor(container: HTMLElement) {
    this.root = document.createElement('div')
    this.root.className = 'video-overlay'
    this.video = document.createElement('video')
    this.video.muted = true
    this.video.playsInline = true
    this.placeholder = document.createElement('div')
    this.placeholder.className = 'video-overlay__placeholder'
    this.placeholder.textContent = '🎬 A little memory… (clip coming soon)'
    const hint = document.createElement('div')
    hint.className = 'video-overlay__hint'
    hint.textContent = 'tap to continue'
    this.root.append(this.video, this.placeholder, hint)
    this.root.addEventListener('pointerdown', () => this.end())
    this.video.addEventListener('ended', () => this.end())
    this.video.addEventListener('error', () => this.showPlaceholder())
    container.appendChild(this.root)
  }

  play(id: string): Promise<void> {
    return new Promise((resolve) => {
      this.finish = resolve
      this.placeholder.style.display = 'none'
      this.video.style.display = 'block'
      this.video.src = `/video/${id}.mp4`
      this.root.classList.add('video-overlay--on')
      this.video.play().catch(() => this.showPlaceholder())
    })
  }

  private showPlaceholder(): void {
    this.video.style.display = 'none'
    this.placeholder.style.display = 'flex'
    if (this.timer !== null) window.clearTimeout(this.timer)
    this.timer = window.setTimeout(() => this.end(), 6000)
  }

  private end(): void {
    if (this.timer !== null) {
      window.clearTimeout(this.timer)
      this.timer = null
    }
    this.root.classList.remove('video-overlay--on')
    this.video.pause()
    this.video.removeAttribute('src')
    const done = this.finish
    this.finish = null
    // даём затухнуть, потом продолжаем сцену
    if (done) window.setTimeout(done, 450)
  }
}
