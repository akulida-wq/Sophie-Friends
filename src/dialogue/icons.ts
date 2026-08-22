/**
 * Icon registry: story JSON references icon KEYS; the visual glyph is a
 * presentation concern. Значения 'img:' указывают на SVG нашего стиля.
 */
const DIR = '/ui/icons'

const ICONS: Record<string, string> = {
  question: `img:${DIR}/question.svg`,
  face_lonely: `img:${DIR}/lonely.svg`,
  face_mad: `img:${DIR}/mad.svg`,
  face_sleepy: `img:${DIR}/sleepy.svg`,
  wave: `img:${DIR}/wave.svg`,
  hide: `img:${DIR}/hiding.svg`,
  hiding: `img:${DIR}/hiding.svg`,
  ball: `img:${DIR}/ball.svg`,
  sparkle: `img:${DIR}/leaf.svg`,
  heart: `img:${DIR}/heart.svg`,
  footstep: `img:${DIR}/footstep.svg`,
  tree: `img:${DIR}/tree.svg`,
  retry: `img:${DIR}/retry.svg`,
  replay: `img:${DIR}/retry.svg`,
  sophie: 'img:/ui/portrait_sophie.png?v=2',
  away: `img:${DIR}/away.svg`,
  friends: `img:${DIR}/friends.svg`,
  leaf: `img:${DIR}/leaf.svg`,
  talk: `img:${DIR}/talk.svg`,
  sun: `img:${DIR}/sun.svg`,
  chalk: `img:${DIR}/sun.svg`,
  later: `img:${DIR}/leaf.svg`,
  tap: `img:${DIR}/tap.svg`,
}

export function iconFor(key: string | undefined): string {
  if (!key) return `img:${DIR}/leaf.svg`
  return ICONS[key] ?? `img:${DIR}/leaf.svg`
}

/** Рендер иконки в элемент: 'img:'-пути становятся <img>, иначе текст. */
export function renderIcon(el: HTMLElement, icon: string): void {
  el.textContent = ''
  if (icon.startsWith('img:')) {
    const img = document.createElement('img')
    img.src = icon.slice(4)
    img.alt = ''
    img.draggable = false
    el.appendChild(img)
  } else {
    el.textContent = icon
  }
}

/** Short human label from a choice id when the JSON gives none. */
export function labelFromId(id: string): string {
  return id.charAt(0).toUpperCase() + id.slice(1).replace(/_/g, ' ')
}
