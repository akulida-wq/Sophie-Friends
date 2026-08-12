import * as THREE from 'three'

/**
 * Grey-box props for the courtyard: ball, blocks, tree, and the NPC Bruno
 * (tall thin blue blob with green sneakers). Placeholder primitives only —
 * replaced by GLB assets in a later phase.
 */

function standard(color: number): THREE.MeshStandardMaterial {
  return new THREE.MeshStandardMaterial({ color, roughness: 0.85 })
}

export function createBall(): THREE.Group {
  const group = new THREE.Group()
  group.name = 'ball'
  const ball = new THREE.Mesh(new THREE.SphereGeometry(0.4, 20, 20), standard(0xe8a87c))
  ball.position.y = 0.4
  ball.castShadow = true
  group.add(ball)
  return group
}

export function createBlocks(): THREE.Group {
  const group = new THREE.Group()
  group.name = 'blocks'
  const colors = [0xc9d98c, 0xa3c4d9, 0xd9b8a3]
  const positions: Array<[number, number, number]> = [
    [0, 0.25, 0],
    [0.6, 0.25, 0.15],
    [0.28, 0.75, 0.05],
  ]
  positions.forEach(([x, y, z], i) => {
    const block = new THREE.Mesh(new THREE.BoxGeometry(0.5, 0.5, 0.5), standard(colors[i]))
    block.position.set(x, y, z)
    block.castShadow = true
    group.add(block)
  })
  return group
}

export function createTree(): THREE.Group {
  const group = new THREE.Group()
  group.name = 'tree'
  const trunk = new THREE.Mesh(new THREE.CylinderGeometry(0.25, 0.32, 1.6, 12), standard(0xa08268))
  trunk.position.y = 0.8
  trunk.castShadow = true
  group.add(trunk)
  const crown = new THREE.Mesh(new THREE.SphereGeometry(1.3, 16, 16), standard(0x8fb37a))
  crown.position.y = 2.4
  crown.castShadow = true
  group.add(crown)
  return group
}

export function createChalk(): THREE.Group {
  const group = new THREE.Group()
  group.name = 'chalk'
  const colors = [0xd98ca3, 0x8cb8d9, 0xd9c98c]
  colors.forEach((color, i) => {
    const stick = new THREE.Mesh(new THREE.CylinderGeometry(0.06, 0.06, 0.5, 8), standard(color))
    stick.rotation.z = Math.PI / 2
    stick.rotation.y = i * 0.6
    stick.position.set(i * 0.18 - 0.18, 0.06, i * 0.1)
    stick.castShadow = true
    group.add(stick)
  })
  return group
}

/** 2–3 background friends playing quietly in the distance (no dialogue). */
export function createFriends(): THREE.Group {
  const group = new THREE.Group()
  group.name = 'friends'
  const colors = [0xd9a3b8, 0xd9cf8c, 0x9cd98c]
  const spots: Array<[number, number]> = [
    [0, 0],
    [1.3, 0.5],
    [0.6, 1.4],
  ]
  colors.forEach((color, i) => {
    const friend = new THREE.Mesh(new THREE.CapsuleGeometry(0.28, 1.0, 8, 12), standard(color))
    friend.position.set(spots[i][0], 0.8, spots[i][1])
    friend.castShadow = true
    friend.name = `friend-${i}`
    group.add(friend)
  })
  return group
}

/** Bruno: tall, thin, blue, green sneakers — withdrawn pose comes later. */
export function createBruno(): THREE.Group {
  const group = new THREE.Group()
  group.name = 'bruno'

  const body = new THREE.Mesh(new THREE.CapsuleGeometry(0.32, 1.5, 8, 16), standard(0x7fa8d9))
  body.position.y = 1.1
  body.castShadow = true
  body.name = 'bruno-body'
  group.add(body)

  const head = new THREE.Mesh(new THREE.SphereGeometry(0.3, 16, 16), standard(0x8fb5e0))
  head.position.y = 2.15
  head.castShadow = true
  head.name = 'bruno-head'
  group.add(head)

  const shoeMaterial = standard(0x6fae6f)
  for (const dx of [-0.16, 0.16]) {
    const shoe = new THREE.Mesh(new THREE.BoxGeometry(0.24, 0.16, 0.42), shoeMaterial)
    shoe.position.set(dx, 0.08, 0.06)
    shoe.castShadow = true
    group.add(shoe)
  }
  return group
}
