/**
 * Icon registry: story JSON references icon KEYS; the visual glyph is a
 * presentation concern. Emoji are grey-phase placeholders for real icons.
 */
const ICONS: Record<string, string> = {
  question: '❓',
  face_lonely: '😔',
  face_mad: '😠',
  face_sleepy: '😴',
  wave: '👋',
  hide: '🙈',
  hiding: '🙈',
  ball: '⚽',
  sparkle: '✨',
  heart: '💛',
  footstep: '👣',
  tree: '🌳',
  retry: '🔁',
  sophie: '🐶',
  away: '🚶',
  replay: '🔁',
  friends: '🧑‍🤝‍🧑',
  leaf: '🍃',
}

export function iconFor(key: string | undefined): string {
  if (!key) return '✨'
  return ICONS[key] ?? '✨'
}

/** Short human label from a choice id when the JSON gives none. */
export function labelFromId(id: string): string {
  return id.charAt(0).toUpperCase() + id.slice(1).replace(/_/g, ' ')
}
