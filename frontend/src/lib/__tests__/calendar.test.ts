import { describe, it, expect } from 'vitest'
import { buildMonthGrid, isAfterToday } from '../calendar'

describe('buildMonthGrid', () => {
  it('月曜始まりで前後の月の日を含めたマス目を返し、今日より後の日を判定できる', () => {
    const grid = buildMonthGrid(2026, 10)

    expect({
      first: grid[0],
      last: grid[grid.length - 1],
      columnOfOctober9: grid.indexOf('2026-10-09') % 7,
      startableOnOctober15: !isAfterToday('2026-10-15', '2026-10-14'),
      startableOnOctober14: !isAfterToday('2026-10-14', '2026-10-14'),
    }).toEqual({
      first: '2026-09-28',
      last: '2026-11-01',
      columnOfOctober9: 4,
      startableOnOctober15: false,
      startableOnOctober14: true,
    })
  })
})
