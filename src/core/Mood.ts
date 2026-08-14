import * as THREE from 'three'
import { audio } from '../audio/AudioSystem'
import type { ColorTemp, MoodSpec } from '../story/types'

/**
 * Scene mood: color temperature eases the sky/fog/sun between cool and
 * warm as Bruno's arc progresses. Music is a logged stub until Task 9.
 */

const TEMPS: Record<ColorTemp, { bg: number; sun: number; sky: number }> = {
  cool: { bg: 0xe2e8ee, sun: 0xefe8dc, sky: 0xeef4fb },
  neutral: { bg: 0xefe8d8, sun: 0xffe8c0, sky: 0xffffff },
  warm: { bg: 0xf6e3c2, sun: 0xffd9a0, sky: 0xffeeda },
}

const EASE = 0.8 // very slow drift — the shift should be felt, not seen

export class Mood {
  private readonly bgCurrent = new THREE.Color()
  private readonly bgTarget = new THREE.Color()
  private readonly sunCurrent = new THREE.Color()
  private readonly sunTarget = new THREE.Color()
  private readonly sun: THREE.DirectionalLight | null
  private readonly skyCurrent = new THREE.Color(0xffffff)
  private readonly skyTarget = new THREE.Color(0xffffff)
  private sky: THREE.Mesh | null | undefined

  constructor(private readonly scene: THREE.Scene) {
    this.sun = scene.getObjectByName('sun') as THREE.DirectionalLight | null
    this.bgCurrent.setHex(TEMPS.neutral.bg)
    this.bgTarget.copy(this.bgCurrent)
    this.sunCurrent.setHex(TEMPS.neutral.sun)
    this.sunTarget.copy(this.sunCurrent)
  }

  apply(mood: MoodSpec | undefined): void {
    if (!mood) return
    if (mood.color_temp) this.setColorTemp(mood.color_temp)
    if (mood.music) {
      console.log(`[Mood] music -> ${mood.music}`)
      audio.setMood(mood.music)
    }
  }

  setColorTemp(temp: ColorTemp): void {
    const target = TEMPS[temp]
    if (!target) return
    console.log(`[Mood] color_temp -> ${temp}`)
    this.bgTarget.setHex(target.bg)
    this.sunTarget.setHex(target.sun)
    this.skyTarget.setHex(target.sky)
  }

  update(dt: number): void {
    const t = 1 - Math.exp(-EASE * dt)
    this.bgCurrent.lerp(this.bgTarget, t)
    this.sunCurrent.lerp(this.sunTarget, t)
    if (this.scene.background instanceof THREE.Color) this.scene.background.copy(this.bgCurrent)
    if (this.scene.fog) this.scene.fog.color.copy(this.bgCurrent)
    if (this.sun) this.sun.color.copy(this.sunCurrent)
    // купол неба подкрашивается настроением (умножение на градиент)
    if (this.sky === undefined) {
      this.sky = (this.scene.getObjectByName('sky-dome') as THREE.Mesh) ?? undefined
      if (this.sky === undefined && this.scene.getObjectByName('environment')) this.sky = null
    }
    if (this.sky) {
      this.skyCurrent.lerp(this.skyTarget, t)
      ;(this.sky.material as THREE.MeshBasicMaterial).color.copy(this.skyCurrent)
    }
  }
}
