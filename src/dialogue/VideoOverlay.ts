import { audio } from '../audio/AudioSystem'
import type { VideoCue } from '../story/types'

const PORTRAITS: Record<string, string> = {
  sophie: '/ui/portrait_sophie.png?v=2',
  bruno: '/ui/portrait_bruno.png?v=2',
}

export interface VideoPlayOptions {
  /** Громкость родной дорожки ролика (0..1). */
  volume?: number
  /** Реплики по таймкоду: голос из /assets/voice + подпись с портретом. */
  cues?: VideoCue[]
}

/**
 * Кино-вставка (как заставки в GTA, только мягко): чёрный letterbox,
 * видео из /video/<id>.mp4. Если файла нет — тёплая плашка-заглушка.
 * Тап в любой момент завершает вставку (правило: выход всегда доступен).
 *
 * Звук ролика — это МИКС в движке: родная дорожка приглушена, поверх —
 * фонтан и птицы (AudioSystem.beginVideoAmbience) и реплики по таймкодам.
 */
export class VideoOverlay {
  private readonly root: HTMLDivElement
  private readonly video: HTMLVideoElement
  private readonly placeholder: HTMLDivElement
  private readonly caption: HTMLDivElement
  private readonly captionPortrait: HTMLImageElement
  private readonly captionText: HTMLSpanElement
  private finish: (() => void) | null = null
  private timer: number | null = null
  private captionTimer: number | null = null
  private cues: VideoCue[] = []
  private firedCues = new Set<number>()

  constructor(container: HTMLElement) {
    this.root = document.createElement('div')
    this.root.className = 'video-overlay'
    this.video = document.createElement('video')
    this.video.playsInline = true
    this.placeholder = document.createElement('div')
    this.placeholder.className = 'video-overlay__placeholder'
    this.placeholder.textContent = '🎬 A little memory… (clip coming soon)'
    const hint = document.createElement('div')
    hint.className = 'video-overlay__hint'
    hint.textContent = 'tap to continue'
    // подпись-реплика поверх ролика
    this.caption = document.createElement('div')
    this.caption.className = 'video-overlay__caption'
    this.captionPortrait = document.createElement('img')
    this.captionPortrait.alt = ''
    this.captionText = document.createElement('span')
    this.caption.append(this.captionPortrait, this.captionText)
    this.root.append(this.video, this.placeholder, this.caption, hint)
    this.root.addEventListener('pointerdown', () => this.end())
    this.video.addEventListener('ended', () => this.end())
    this.video.addEventListener('error', () => this.showPlaceholder())
    this.video.addEventListener('timeupdate', () => this.checkCues())
    container.appendChild(this.root)
  }

  play(id: string, opts: VideoPlayOptions = {}): Promise<void> {
    return new Promise((resolve) => {
      this.finish = resolve
      this.cues = [...(opts.cues ?? [])].sort((a, b) => a.at - b.at)
      this.firedCues.clear()
      this.placeholder.style.display = 'none'
      this.video.style.display = 'block'
      this.video.muted = false
      this.video.volume = Math.min(1, Math.max(0, opts.volume ?? 0.35))
      this.video.src = `/video/${id}.mp4`
      this.root.classList.add('video-overlay--on')
      audio.beginVideoAmbience()
      this.video.play().catch(() => this.showPlaceholder())
    })
  }

  private checkCues(): void {
    const t = this.video.currentTime
    this.cues.forEach((cue, i) => {
      if (this.firedCues.has(i) || t < cue.at) return
      this.firedCues.add(i)
      audio.voice(cue.voice)
      this.showCaption(cue)
    })
  }

  private showCaption(cue: VideoCue): void {
    const speaker = cue.actor === 'bruno' ? 'bruno' : 'sophie'
    this.captionPortrait.src = PORTRAITS[speaker]
    this.captionText.textContent = cue.line
    this.caption.classList.add('video-overlay__caption--on')
    if (this.captionTimer !== null) window.clearTimeout(this.captionTimer)
    this.captionTimer = window.setTimeout(() => {
      this.caption.classList.remove('video-overlay__caption--on')
      this.captionTimer = null
    }, Math.min(5000, Math.max(2200, 1200 + cue.line.length * 55)))
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
    if (this.captionTimer !== null) {
      window.clearTimeout(this.captionTimer)
      this.captionTimer = null
    }
    this.caption.classList.remove('video-overlay__caption--on')
    this.root.classList.remove('video-overlay--on')
    this.video.pause()
    this.video.removeAttribute('src')
    audio.endVideoAmbience()
    const done = this.finish
    this.finish = null
    // даём затухнуть, потом продолжаем сцену
    if (done) window.setTimeout(done, 450)
  }
}
