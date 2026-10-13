import { describe, it, expect } from 'vitest'
import { buildMonthGrid, isAfterToday } from '../calendar'

describe('buildMonthGrid', () => {
  it('月曜始まりで前後の月の日を含めたマス目を返し、今日より後の日を判定できる', () => {
    const grid = buildMonthGrid(2026, 10)

    expect({
      first: grid[0],
      last: grid[grid.length - 1],
      cellCount: grid.length,
      columnOfOctober9: grid.indexOf('2026-10-09') % 7,
      startableOnOctober15: !isAfterToday('2026-10-15', '2026-10-14'),
      startableOnOctober14: !isAfterToday('2026-10-14', '2026-10-14'),
    }).toEqual({
      first: '2026-09-28',
      last: '2026-11-01',
      cellCount: 35,
      columnOfOctober9: 4,
      startableOnOctober15: false,
      startableOnOctober14: true,
    })
  })

  it.each([
    { case: '6行になる', year: 2026, month: 8, first: '2026-07-27', last: '2026-09-06', cellCount: 42 },
    { case: '4行になる', year: 2027, month: 2, first: '2027-02-01', last: '2027-02-28', cellCount: 28 },
  ])('$year年$month月は$case', ({ year, month, first, last, cellCount }) => {
    const grid = buildMonthGrid(year, month)

    expect({ first: grid[0], last: grid[grid.length - 1], cellCount: grid.length }).toEqual({ first, last, cellCount })
  })

  it.each([
    { case: '1日が月曜の', month: 6, first: '2026-06-01', last: '2026-07-05' },
    { case: '末日が日曜の', month: 5, first: '2026-04-27', last: '2026-05-31' },
  ])('$case 2026年$month月は、$first から $last までの35マスになる', ({ month, first, last }) => {
    const grid = buildMonthGrid(2026, month)

    expect({ first: grid[0], last: grid[grid.length - 1], cellCount: grid.length }).toEqual({
      first,
      last,
      cellCount: 35,
    })
  })
})
