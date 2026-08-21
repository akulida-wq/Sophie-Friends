import * as THREE from 'three'
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js'

export type PropId = 'ball' | 'chalk' | 'blocks' | 'tree'

export interface LoadedEnvironment {
  root: THREE.Group
  props: Partial<Record<PropId, THREE.Object3D>>
}

const PROP_NODES: Record<PropId, string> = {
  ball: 'Ball',
  chalk: 'Chalk',
  blocks: 'Blocks',
  tree: 'Tree',
}

/**
 * Playground GLB replaces the grey-box world. The GLB's `Ground` mesh is
 * renamed to `ground` so the movement raycast keeps working unchanged;
 * story props (Ball/Chalk/Blocks/Tree) are exposed for the interaction
 * system. Prop materials are cloned so the glow pulse never lights up
 * unrelated meshes that share a material (e.g. Tree crown vs bushes).
 */
/** Уютная полукруглая расстановка: сдвиги узлов площадки (dx, dz). */
const LAYOUT_SHIFT: Record<string, [number, number]> = {
  Slide: [-1.5, 1.8],
  Swing: [1.4, 3.9],
  Sandbox: [0, 1.3],
  TreeDeco2: [0.5, 2.5],
}

/** Двор: кликабельный квадратный газон (raycast ходьбы идёт по 'ground'). */
function buildLawnSquare(): THREE.Mesh {
  const HALF = 16.6
  const geo = new THREE.PlaneGeometry(HALF * 2, HALF * 2, 64, 64)
  geo.rotateX(-Math.PI / 2)
  const pos = geo.attributes.position
  const colors = new Float32Array(pos.count * 3)
  const light = new THREE.Color(0x8aba71)
  const deep = new THREE.Color(0x6da05a)
  const c = new THREE.Color()
  for (let i = 0; i < pos.count; i++) {
    const x = pos.getX(i)
    const z = pos.getZ(i)
    const n = (Math.sin(x * 0.9 + z * 0.55) + Math.sin(x * 0.35 - z * 1.15) + 2) / 4
    const speck = Math.sin(x * 7.3 + z * 5.1) * Math.sin(x * 3.7 - z * 8.2) * 0.05
    c.copy(light).lerp(deep, Math.min(1, Math.max(0, n + speck)))
    colors[i * 3] = c.r
    colors[i * 3 + 1] = c.g
    colors[i * 3 + 2] = c.b
  }
  geo.setAttribute('color', new THREE.BufferAttribute(colors, 3))
  // Lambert: IBL-окружение его не касается вовсе — матовый как настоящий газон
  const mesh = new THREE.Mesh(
    geo,
    new THREE.MeshLambertMaterial({ vertexColors: true }),
  )
  mesh.name = 'ground'
  mesh.receiveShadow = true
  return mesh
}

/** Территория за забором: суше и бледнее; НЕ 'ground' — туда не сходить. */
function buildOuterGround(): THREE.Mesh {
  // Тот же газон, но огромный — край уходит в туман цвета неба, поэтому
  // переход земля -> небо плавный. НЕ 'ground' — ходить туда нельзя.
  const geo = new THREE.PlaneGeometry(150, 150, 48, 48)
  geo.rotateX(-Math.PI / 2)
  const pos = geo.attributes.position
  const colors = new Float32Array(pos.count * 3)
  const light = new THREE.Color(0x8aba71)
  const deep = new THREE.Color(0x6da05a)
  const c = new THREE.Color()
  for (let i = 0; i < pos.count; i++) {
    const x = pos.getX(i)
    const z = pos.getZ(i)
    const n = (Math.sin(x * 0.5 + z * 0.3) + Math.sin(x * 0.21 - z * 0.6) + 2) / 4
    const speck = Math.sin(x * 7.3 + z * 5.1) * Math.sin(x * 3.7 - z * 8.2) * 0.05
    c.copy(light).lerp(deep, Math.min(1, Math.max(0, n + speck)))
    colors[i * 3] = c.r
    colors[i * 3 + 1] = c.g
    colors[i * 3 + 2] = c.b
  }
  geo.setAttribute('color', new THREE.BufferAttribute(colors, 3))
  const mesh = new THREE.Mesh(
    geo,
    new THREE.MeshLambertMaterial({ vertexColors: true }),
  )
  mesh.name = 'ground-outer'
  mesh.position.y = -0.03
  mesh.receiveShadow = true
  return mesh
}

/** Небо: купол с вертикальным градиентом (голубой -> кремовый горизонт). */
function buildSkyDome(): THREE.Mesh {
  const R = 155
  const geo = new THREE.SphereGeometry(R, 48, 28)
  const pos = geo.attributes.position
  const colors = new Float32Array(pos.count * 3)
  const top = new THREE.Color(0x6db8ea)
  const mid = new THREE.Color(0x9fd3f2)
  const horizon = new THREE.Color(0xdcecf4)
  const c = new THREE.Color()
  for (let i = 0; i < pos.count; i++) {
    const t = Math.min(1, Math.max(0, pos.getY(i) / R))
    if (t < 0.3) c.copy(horizon).lerp(mid, Math.pow(t / 0.3, 0.7))
    else c.copy(mid).lerp(top, Math.pow((t - 0.3) / 0.7, 0.9))
    colors[i * 3] = c.r
    colors[i * 3 + 1] = c.g
    colors[i * 3 + 2] = c.b
  }
  geo.setAttribute('color', new THREE.BufferAttribute(colors, 3))
  const mesh = new THREE.Mesh(
    geo,
    new THREE.MeshBasicMaterial({ side: THREE.BackSide, vertexColors: true, fog: false }),
  )
  mesh.name = 'sky-dome'
  return mesh
}

/** Трава: InstancedMesh из узла GrassTuft (v2), рассыпанная по острову. */
function buildGrass(root: THREE.Group): void {
  const srcNode = root.getObjectByName('GrassTuft')
  if (!srcNode) return
  let src: THREE.Mesh | null = null
  srcNode.traverse((ch) => {
    if (!src && (ch as THREE.Mesh).isMesh) src = ch as THREE.Mesh
  })
  srcNode.visible = false
  if (!src) return
  const tuft = src as THREE.Mesh
  const COUNT = 3600
  const inst = new THREE.InstancedMesh(tuft.geometry, tuft.material, COUNT)
  // детерминированный PRNG: трава не «пересеивается» между кадрами/сессиями
  let seed = 20260820
  const rand = () => {
    seed = (seed * 16807) % 2147483647
    return seed / 2147483647
  }
  // не сажаем траву в дом, объекты и на плиточную дорожку
  const AVOID_C: [number, number, number][] = [
    [-3.0, -11.6, 1.7], [4.4, -12.6, 2.0], [7.4, -9.4, 2.2],
    [6.2, 8.6, 1.4], [-8.6, -6.4, 1.3], [8.6, 5.4, 0.7],
    [-9.4, -2.0, 1.0], [-5.6, 3.4, 0.9],
    [-5.5, 9.6, 1.9], // фонтан
    [4.25, -8.05, 0.8], [5.75, -7.05, 0.75], [6.55, -9.35, 0.8], // друзья
  ]
  const AVOID_R: [number, number, number, number][] = [
    [6.6, 13.8, -6.2, 0.2], // дом справа (x0,x1,z0,z1)
  ]
  // Клетки дорожки — ТА ЖЕ сетка, что кладёт плитку в build_environment2.py:
  // ни один пучок не может прорасти сквозь плиту.
  const P = 1.06
  const G0 = 0.87
  const tileCells = new Set<string>()
  const addRun = (xs: number[], zs: number[]) => {
    for (const kx of xs) for (const kz of zs) tileCells.add(`${kx},${kz}`)
  }
  const range = (a: number, b: number) => {
    const out: number[] = []
    for (let k = a; k < b; k++) out.push(k)
    return out
  }
  addRun(range(-16, 14), [0, 1])     // главная: ворота -> дом
  addRun([0, 1], range(-13, 0))      // ветка на площадку
  addRun([13], range(-7, 0))         // кольцо: восток
  addRun(range(5, 14), [-7])         // кольцо: север
  addRun([5], range(-7, 0))          // кольцо: запад (крыльцо)
  addRun([-6], range(2, 9))          // южная ветка: к фонтану
  addRun([5], range(2, 7))           // южная ветка: к лавке
  const onTile = (x: number, z: number): boolean => {
    const kx = Math.round((x - G0) / P)
    const kz = Math.round((z - G0) / P)
    if (!tileCells.has(`${kx},${kz}`)) return false
    return (
      Math.abs(x - (G0 + kx * P)) < 0.62 && Math.abs(z - (G0 + kz * P)) < 0.62
    )
  }
  const dummy = new THREE.Object3D()
  let placed = 0
  const HALF = 15.4
  const OUT_COUNT = 1000 // редкая трава на внешней территории (кроме улицы)
  while (placed < COUNT) {
    const outer = placed >= COUNT - OUT_COUNT
    let x: number
    let z: number
    if (outer) {
      x = -14 + rand() * 46      // восточнее улицы: x in [-14, 32]
      z = (rand() * 2 - 1) * 31
      if (Math.abs(x) < 16.4 && Math.abs(z) < 16.4) continue // двор отдельно
      if (Math.max(Math.abs(x), Math.abs(z)) > 31.5) continue
    } else {
      x = (rand() * 2 - 1) * HALF
      z = (rand() * 2 - 1) * HALF
      if (AVOID_C.some(([ax, az, ar]) => Math.hypot(x - ax, z - az) < ar)) continue
      if (AVOID_R.some(([x0, x1, z0, z1]) => x > x0 && x < x1 && z > z0 && z < z1))
        continue
      if (onTile(x, z)) continue
    }
    dummy.position.set(x, 0, z)
    dummy.rotation.y = rand() * Math.PI * 2
    const s = 0.3 + rand() * 0.35
    dummy.scale.setScalar(s)
    dummy.updateMatrix()
    inst.setMatrixAt(placed++, dummy.matrix)
  }
  inst.receiveShadow = true
  inst.name = 'grass'
  root.add(inst)
}

/** Препятствия двора: Софи не проходит сквозь объекты и забор. */
const YARD_BOUND = 15.2
const COLL_CIRCLES: [number, number, number][] = [
  [-3.0, -11.6, 1.5], [4.4, -12.6, 1.7], [7.4, -9.4, 1.9],
  [6.2, 8.6, 1.1],
  // стволы деревьев (крона не мешает)
  [-8.6, -6.4, 0.6], [-13.6, -13.4, 0.6], [13.5, -13.6, 0.6],
  [-12.6, 11.8, 0.6],
  // кусты
  [-6.2, -13.9, 0.8], [13.9, -7.2, 0.7], [-14.3, -2.0, 0.75],
  [10.4, 13.6, 0.7], [14.2, 9.0, 0.75], [-8.8, 13.9, 0.7],
  [0.6, 13.8, 0.7], [13.8, 1.4, 0.65],
  // Бруно и друзья (жёлтый/розовый/красный)
  [-3.0, -8.0, 0.9],
  [4.25, -8.05, 0.75], [5.75, -7.05, 0.7], [6.55, -9.35, 0.75],
  // фонтан
  [-5.5, 9.6, 1.5],
]
const COLL_RECTS: [number, number, number, number][] = [
  [6.9, 13.5, -5.9, -0.1], // дом
]

export function resolveYardCollisions(pos: THREE.Vector3): void {
  pos.x = Math.min(YARD_BOUND, Math.max(-YARD_BOUND, pos.x))
  pos.z = Math.min(YARD_BOUND, Math.max(-YARD_BOUND, pos.z))
  for (const [cx, cz, r] of COLL_CIRCLES) {
    const dx = pos.x - cx
    const dz = pos.z - cz
    const d = Math.hypot(dx, dz)
    if (d < r && d > 1e-5) {
      pos.x = cx + (dx / d) * r
      pos.z = cz + (dz / d) * r
    }
  }
  for (const [x0, x1, z0, z1] of COLL_RECTS) {
    if (pos.x > x0 && pos.x < x1 && pos.z > z0 && pos.z < z1) {
      const pushes: [number, number, number][] = [
        [pos.x - x0, -1, 0], [x1 - pos.x, 1, 0],
        [pos.z - z0, 0, -1], [z1 - pos.z, 0, 1],
      ]
      pushes.sort((a, b) => a[0] - b[0])
      const [d, nx, nz] = pushes[0]
      pos.x += nx * d
      pos.z += nz * d
    }
  }
}

export async function loadEnvironment(url: string): Promise<LoadedEnvironment> {
  const gltf = await new GLTFLoader().loadAsync(url)
  const root = gltf.scene
  root.name = 'environment'
  root.traverse((child) => {
    if ((child as THREE.Mesh).isMesh) {
      child.castShadow = true
      child.receiveShadow = true
    }
  })

  // Плоская GLB-земля (только в старом environment.glb) прячется,
  // вместо неё — скруглённый остров-газон.
  const flatGround = root.getObjectByName('Ground')
  if (flatGround) {
    flatGround.visible = false
    flatGround.name = 'ground-flat'
    // Композиция старого набора: полукруглой сценой, а не в линию.
    for (const [nodeName, [dx, dz]] of Object.entries(LAYOUT_SHIFT)) {
      const node = root.getObjectByName(nodeName)
      if (node) {
        node.position.x += dx
        node.position.z += dz
      }
    }
  }
  root.add(buildLawnSquare())
  root.add(buildOuterGround())
  root.add(buildSkyDome())
  buildGrass(root)

  const props: Partial<Record<PropId, THREE.Object3D>> = {}
  for (const [id, nodeName] of Object.entries(PROP_NODES) as [PropId, string][]) {
    const node = root.getObjectByName(nodeName)
    if (!node) {
      console.warn(`[Environment] prop "${nodeName}" missing in GLB`)
      continue
    }
    node.traverse((child) => {
      const mesh = child as THREE.Mesh
      if (mesh.isMesh) mesh.material = (mesh.material as THREE.Material).clone()
    })
    props[id] = node
  }
  console.log(`[Environment] loaded (${Object.keys(props).join(', ')})`)
  return { root, props }
}
