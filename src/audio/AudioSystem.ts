/**
 * Звук мока. Safety-правила прежде всего: ничего резкого и громкого.
 *
 * - Эмбиент: процедурный пад (WebAudio, синусы/треугольники через lowpass
 *   с медленным LFO). Два слоя: base (calm) + warm; смены — медленные
 *   рампы по 4с, никаких скачков. ambient_calm / ambient_warm /
 *   ambient_warm_lift из story JSON.
 * - UI-звуки: короткие мягкие блипы с плавной атакой, громкость низкая.
 * - Озвучка: /assets/voice/{line_id}.mp3; если файла нет — тихо живём
 *   с текстовым пузырём (один warn на id).
 *
 * AudioContext стартует только после первого жеста пользователя.
 */

type MoodMusic = 'ambient_calm' | 'ambient_warm' | 'ambient_warm_lift'
type UiSound = 'tap' | 'card' | 'cue' | 'reward'

const MASTER_VOLUME = 0.22
const VOICE_VOLUME = 0.9

class AudioSystem {
  private ctx: AudioContext | null = null
  private master: GainNode | null = null
  private warmGain: GainNode | null = null
  private liftGain: GainNode | null = null
  private started = false
  private pendingMood: MoodMusic = 'ambient_calm'
  private readonly missingVoices = new Set<string>()

  constructor() {
    const unlock = () => {
      this.ensure()
      window.removeEventListener('pointerdown', unlock)
    }
    window.addEventListener('pointerdown', unlock)
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
    if (this.ctx.state === 'suspended') void this.ctx.resume()
    if (!this.started) {
      this.started = true
      this.buildAmbient()
      this.setMood(this.pendingMood)
    }
    return this.ctx
  }

  /** Пад: базовый слой всегда, тёплые слои подмешиваются рампами. */
  private buildAmbient(): void {
    const ctx = this.ctx
    if (!ctx || !this.master) return

    const pad = (freqs: number[], type: OscillatorType, cutoff: number) => {
      const gain = ctx.createGain()
      const filter = ctx.createBiquadFilter()
      filter.type = 'lowpass'
      filter.frequency.value = cutoff
      filter.connect(gain)
      gain.connect(this.master as GainNode)
      for (const f of freqs) {
        const osc = ctx.createOscillator()
        osc.type = type
        osc.frequency.value = f
        // лёгкая расстройка для живости
        osc.detune.value = (Math.random() - 0.5) * 6
        osc.connect(filter)
        osc.start()
      }
      // медленное "дыхание" фильтра — никакого мерцания
      const lfo = ctx.createOscillator()
      lfo.frequency.value = 0.05
      const lfoGain = ctx.createGain()
      lfoGain.gain.value = cutoff * 0.25
      lfo.connect(lfoGain)
      lfoGain.connect(filter.frequency)
      lfo.start()
      return gain
    }

    const base = pad([110, 164.8, 220], 'triangle', 420) // A2+E3+A3, открытая квинта
    base.gain.value = 0.5
    this.warmGain = pad([277.2, 329.6], 'sine', 700) // C#4+E4 — мажорное тепло
    this.warmGain.gain.value = 0
    this.liftGain = pad([440, 554.4], 'sine', 900) // A4+C#5 — мягкий подъём
    this.liftGain.gain.value = 0
  }

  /** Смена настроения музыки — медленный кроссфейд (4с). */
  setMood(music: string): void {
    this.pendingMood = (music as MoodMusic) ?? 'ambient_calm'
    const ctx = this.ctx
    if (!ctx || !this.warmGain || !this.liftGain) return
    const t = ctx.currentTime
    const ramp = (g: GainNode, v: number) => {
      g.gain.cancelScheduledValues(t)
      g.gain.setValueAtTime(g.gain.value, t)
      g.gain.linearRampToValueAtTime(v, t + 4)
    }
    if (music === 'ambient_warm_lift') {
      ramp(this.warmGain, 0.3)
      ramp(this.liftGain, 0.22)
    } else if (music === 'ambient_warm') {
      ramp(this.warmGain, 0.32)
      ramp(this.liftGain, 0.08)
    } else {
      ramp(this.warmGain, 0)
      ramp(this.liftGain, 0)
    }
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
    if (!id || this.missingVoices.has(id)) return
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
