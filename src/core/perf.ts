/**
 * Лёгкий режим для слабых устройств (старые iPad, бюджетные планшеты).
 * Главные пожиратели кадров на них: ретина-разрешение (fill rate), теневой
 * проход по всей геометрии двора и плотность травы.
 */
function detectLite(): boolean {
  // iPadOS прикидывается макбуком: MacIntel + тач
  const isIOS =
    /iPad|iPhone|iPod/.test(navigator.userAgent) ||
    (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1)
  const slowCpu = (navigator.hardwareConcurrency ?? 8) <= 4
  const lowMem =
    'deviceMemory' in navigator &&
    ((navigator as { deviceMemory?: number }).deviceMemory ?? 8) <= 4
  return isIOS || slowCpu || lowMem
}

export const LITE = detectLite()

/** Пиксельная плотность: на слабых — заметно ниже ретины. */
export const MAX_PIXEL_RATIO = LITE ? 1.3 : 2

/** Тени на слабых устройствах отключены целиком (второй проход по сцене). */
export const SHADOWS_ENABLED = !LITE

/** Трава: вдвое реже в лёгком режиме. */
export const GRASS_COUNT = LITE ? 1800 : 3600

if (LITE) console.log('[Perf] lite mode: no shadows, dpr<=1.3, less grass')
