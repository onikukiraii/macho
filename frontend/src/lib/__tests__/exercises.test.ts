import { describe, it, expect } from 'vitest'
import { formatSet } from '../exercises'

describe('formatSet', () => {
  it.each([
    [{ order: 1, weight: 100, reps: 5, rir: null }, '100 kg × 5'],
    [{ order: 1, weight: 100, reps: 5, rir: 2 }, '100 kg × 5 RIR 2'],
  ])('%j を %s にする', (set, expected) => {
    expect(formatSet(set)).toBe(expected)
  })
})
