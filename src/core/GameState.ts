export type GameState = 'EXPLORE' | 'CHOICE' | 'CINEMATIC' | 'PAUSED'

type StateListener = (from: GameState, to: GameState) => void

/**
 * Central game state machine. All systems ask this class what state the
 * game is in; transitions are logged so they can be followed in the console.
 */
export class GameStateMachine {
  private current: GameState = 'EXPLORE'
  private listeners: StateListener[] = []

  get state(): GameState {
    return this.current
  }

  is(state: GameState): boolean {
    return this.current === state
  }

  transition(to: GameState): void {
    if (to === this.current) return
    const from = this.current
    this.current = to
    console.log(`[GameState] ${from} -> ${to}`)
    for (const listener of this.listeners) listener(from, to)
  }

  onChange(listener: StateListener): void {
    this.listeners.push(listener)
  }
}
