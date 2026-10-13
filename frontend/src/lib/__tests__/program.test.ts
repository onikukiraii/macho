import { describe, it, expect } from 'vitest'
import { formatDayLabel } from '../program'

describe('formatDayLabel', () => {
  it('週と Day の番号を「第N週 DayM」にする', () => {
    expect(formatDayLabel({ week: 3, day: 1 })).toBe('第3週 Day1')
  })
})
