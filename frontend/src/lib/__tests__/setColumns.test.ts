import { describe, it, expect } from 'vitest'
import { appendColumn, copyPreviousColumn, fillWeightForward, toSetParams, type SetColumn } from '../setColumns'

const EMPTY_COLUMN: SetColumn = { weight: '', reps: '', rir: null }

describe('fillWeightForward', () => {
  it('後ろの空の列に重量を入れ、重量が入力済みの列は変えない', () => {
    const columns: SetColumn[] = [
      { weight: '102.5', reps: '', rir: null },
      EMPTY_COLUMN,
      EMPTY_COLUMN,
      EMPTY_COLUMN,
      { weight: '100', reps: '', rir: null },
    ]

    expect(fillWeightForward(columns, 0).map((column) => column.weight)).toEqual(['102.5', '102.5', '102.5', '102.5', '100'])
  })
})

describe('toSetParams', () => {
  it('重量と回数の両方が入った列だけを、列の位置を番号にして返す', () => {
    const columns: SetColumn[] = [
      { weight: '102.5', reps: '5', rir: 2 },
      { weight: '102.5', reps: '', rir: null },
      { weight: '100', reps: '6', rir: null },
    ]

    expect(toSetParams(columns)).toEqual([
      { order: 1, weight: 102.5, reps: 5, rir: 2 },
      { order: 3, weight: 100, reps: 6, rir: null },
    ])
  })
})

describe('copyPreviousColumn', () => {
  it('前の列の重量・回数・RIR を指定した列に入れる', () => {
    const columns: SetColumn[] = [
      { weight: '102.5', reps: '5', rir: 2 },
      { weight: '100', reps: '6', rir: 1 },
      EMPTY_COLUMN,
    ]

    expect(copyPreviousColumn(columns, 2)[2]).toEqual({ weight: '100', reps: '6', rir: 1 })
  })
})

describe('appendColumn', () => {
  it('末尾に空の列を1つ足す', () => {
    const columns: SetColumn[] = [{ weight: '102.5', reps: '5', rir: 2 }]

    expect(appendColumn(columns)).toEqual([{ weight: '102.5', reps: '5', rir: 2 }, EMPTY_COLUMN])
  })
})
