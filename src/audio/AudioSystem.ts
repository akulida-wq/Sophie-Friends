/**
 * Звук мока. Safety-правила прежде всего: ничего резкого и громкого.
 *
 * - Музыка: «музыкальная шкатулка» — мягкие колокольчики, мажорная
 *   пентатоника, спокойный темп + тихий пад-фон. Слои настроения
 *   (calm / warm / warm_lift) подмешивают гармонию и тепло медленными
 *   рампами, без скачков.
 * - UI-звуки: короткие мягкие блипы с плавной атакой.
 * - Озвучка: /assets/voice/{line_id}.mp3; нет файла — текстовый пузырь.
 *
 * AudioContext стартует после первого жеста. Фоновая вкладка, пауза игры
 * и кнопка mute глушат звук полностью.
 */

type MoodMusic = 'ambient_calm' | 'ambient_warm' | 'ambient_warm_lift'
type UiSound = 'tap' | 'card' | 'cue' | 'reward'

const MASTER_VOLUME = 0.22
const VOICE_VOLUME = 0.9
const MUTE_KEY = 'sophie_sound_muted'

const STEP = 0.33 // восьмые при ~90 bpm — неторопливо
// A-мажорная пентатоника, простенький напев с паузами (0 = пауза).
const MELODY = [
  440.0, 0, 554.4, 659.3, 0, 554.4, 440.0, 0,
  493.9, 554.4, 0, 659.3, 554.4, 0, 493.9, 0,
  440.0, 0, 659.3, 0, 740.0, 659.3, 554.4, 0,
  493.9, 0, 554.4, 493.9, 440.0, 0, 0, 0,
]
// Тёплый второй голос (терции/квинты), включается на warm/lift.
const HARMONY = [
  0, 0, 659.3, 0, 0, 659.3, 554.4, 0,
  0, 659.3, 0, 740.0, 659.3, 0, 0, 0,
  554.4, 0, 740.0, 0, 880.0, 0, 659.3, 0,
  0, 0, 659.3, 0, 554.4, 0, 0, 0,
]

class AudioSystem {
  private ctx: AudioContext | null = null
  private master: GainNode | null = null
  private melodyGain: GainNode | null = null
  private harmonyGain: GainNode | null = null
  private started = false
  private pendingMood: MoodMusic = 'ambient_calm'
  private readonly missingVoices = new Set<string>()
  private userPaused = false
  private muted = false
  private schedulerId: number | null = null
  private nextNoteTime = 0
  private step = 0

  constructor() {
    this.muted = localStorage.getItem(MUTE_KEY) === '1'
    const unlock = () => {
      this.ensure()
      window.removeEventListener('pointerdown', unlock)
    }
    window.addEventListener('pointerdown', unlock)
    // Фоновая вкладка не должна звучать.
    document.addEventListener('visibilitychange', () => this.applyState())
  }

  get isMuted(): boolean {
    return this.muted
  }

  /** Кнопка звука в игре. Возвращает новое состояние muted. */
  toggleMuted(): boolean {
    this.muted = !this.muted
    localStorage.setItem(MUTE_KEY, this.muted ? '1' : '0')
    this.ensure()
    this.applyState()
    return this.muted
  }

  /** Пауза игры глушит весь звук; резюм возвращает. */
  suspend(): void {
    this.userPaused = true
    this.applyState()
  }

  resume(): void {
    this.userPaused = false
    this.applyState()
  }

  private applyState(): void {
    if (!this.ctx) return
    if (this.muted || this.userPaused || document.hidden) void this.ctx.suspend()
    else void this.ctx.resume()
  }

  private ensure(): AudioContext | null {
    if (!this.ctx) {
      try {
        this.ctx = new AudioContext()
      } catch {
        return null
      }
      this.master = this.ctx.createGain()
      this.master.gain.value = MASTER_VOLUME
      this.master.connect(this.ctx.destination)
    }
    if (!this.started) {
      this.started = true
      this.buildAmbient()
      this.startScheduler()
      this.setMood(this.pendingMood)
    }
    this.applyState()
    return this.ctx
  }

  /** Только шины мелодии/гармонии — никаких непрерывных падов. */
  private buildAmbient(): void {
    const ctx = this.ctx
    if (!ctx || !this.master) return

    this.melodyGain = ctx.createGain()
    this.melodyGain.gain.value = 0.85
    this.melodyGain.connect(this.master)
    this.harmonyGain = ctx.createGain()
    this.harmonyGain.gain.value = 0
    this.harmonyGain.connect(this.master)
  }

  /** Колокольчик «музыкальной шкатулки»: синус + тихая октава, быстрый
   *  мягкий спад. Никаких резких атак. */
  private bell(freq: number, at: number, vol: number, dest: GainNode): void {
    const ctx = this.ctx
    if (!ctx) return
    for (const [mult, share] of [[1, 1], [2, 0.25]] as const) {
      const osc = ctx.createOscillator()
      osc.type = 'sine'
      osc.frequency.value = freq * mult
      const g = ctx.createGain()
      g.gain.setValueAtTime(0, at)
      g.gain.linearRampToValueAtTime(vol * share, at + 0.02)
      g.gain.exponentialRampToValueAtTime(0.0001, at + 0.55)
      osc.connect(g)
      g.connect(dest)
      osc.start(at)
      osc.stop(at + 0.6)
    }
  }

  /** Планировщик нот с небольшим лукахедом; на suspend время замирает. */
  private startScheduler(): void {
    const ctx = this.ctx
    if (!ctx || this.schedulerId !== null) return
    this.nextNoteTime = ctx.currentTime + 0.15
    this.schedulerId = window.setInterval(() => {
      if (!this.ctx || !this.melodyGain || !this.harmonyGain) return
      while (this.nextNoteTime < this.ctx.currentTime + 0.6) {
        const i = this.step % MELODY.length
        const note = MELODY[i]
        if (note > 0) {
          const vel = 0.11 + (i % 8 === 0 ? 0.03 : 0) // лёгкий акцент на такт
          this.bell(note, this.nextNoteTime, vel, this.melodyGain)
        }
        const h = HARMONY[i]
        if (h > 0) this.bell(h, this.nextNoteTime, 0.08, this.harmonyGain)
        this.step++
        this.nextNoteTime += STEP
      }
    }, 250)
  }

  /** Смена настроения — медленный кроссфейд (4с). */
  setMood(music: string): void {
    this.pendingMood = (music as MoodMusic) ?? 'ambient_calm'
    const ctx = this.ctx
    if (!ctx || !this.harmonyGain) return
    const t = ctx.currentTime
    const ramp = (g: GainNode, v: number) => {
      g.gain.cancelScheduledValues(t)
      g.gain.setValueAtTime(g.gain.value, t)
      g.gain.linearRampToValueAtTime(v, t + 4)
    }
    if (music === 'ambient_warm_lift') ramp(this.harmonyGain, 0.9)
    else if (music === 'ambient_warm') ramp(this.harmonyGain, 0.6)
    else ramp(this.harmonyGain, 0)
  }

  /** Короткий мягкий тон с плавной атакой (без щелчков). */
  private blip(freq: number, at: number, dur = 0.14, vol = 0.07): void {
    const ctx = this.ctx
    if (!ctx || !this.master) return
    const osc = ctx.createOscillator()
    osc.type = 'sine'
    osc.frequency.value = freq
    const gain = ctx.createGain()
    const t = ctx.currentTime + at
    gain.gain.setValueAtTime(0, t)
    gain.gain.linearRampToValueAtTime(vol, t + 0.02)
    gain.gain.exponentialRampToValueAtTime(0.0001, t + dur)
    osc.connect(gain)
    gain.connect(this.master)
    osc.start(t)
    osc.stop(t + dur + 0.05)
  }

  ui(sound: UiSound): void {
    if (!this.ensure()) return
    switch (sound) {
      case 'tap':
        this.blip(523, 0, 0.12, 0.05)
        break
      case 'card':
        this.blip(392, 0, 0.12, 0.06)
        this.blip(523, 0.09, 0.16, 0.06)
        break
      case 'cue':
        this.blip(659, 0, 0.14, 0.05)
        break
      case 'reward': // тёплое мягкое арпеджио
        this.blip(523, 0, 0.2, 0.06)
        this.blip(659, 0.16, 0.2, 0.06)
        this.blip(784, 0.32, 0.3, 0.05)
        break
    }
  }

  /** Озвучка реплики; текстовый пузырь — всегда рядом как фолбэк. */
  voice(id: string | undefined): void {
    if (!id || this.muted || this.missingVoices.has(id)) return
    const el = new Audio(`/assets/voice/${id}.mp3`)
    el.volume = VOICE_VOLUME
    el.onerror = () => {
      if (!this.missingVoices.has(id)) {
        this.missingVoices.add(id)
        console.warn(`[Voice] нет файла для "${id}" — только текстовый пузырь`)
      }
    }
    el.play().catch(() => {
      /* до первого жеста браузер может отклонить — это ок */
    })
  }
}

/** Глобальный сервис звука (лист-модуль, импортируется откуда угодно). */
export const audio = new AudioSystem()
