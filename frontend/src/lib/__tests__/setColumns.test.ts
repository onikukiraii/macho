import { describe, it, expect } from 'vitest'
import {
  appendColumn,
  copyPreviousColumn,
  fillWeightForward,
  isValidReps,
  isValidWeight,
  toSetParams,
  type SetColumn,
} from '../setColumns'

const EMPTY_COLUMN: SetColumn = { weight: '', reps: '', rir: null }

describe('fillWeightForward', () => {
  it('後ろの空の列に重量を入れ、重量が入力済みの列は変えない', () => {
    const columns: SetColumn[] = [
      EMPTY_COLUMN,
      { weight: '102.5', reps: '5', rir: 2 },
      EMPTY_COLUMN,
      { weight: '', reps: '3', rir: 1 },
      { weight: '100', reps: '', rir: null },
    ]

    expect(fillWeightForward(columns, 1)).toEqual([
      EMPTY_COLUMN,
      { weight: '102.5', reps: '5', rir: 2 },
      { weight: '102.5', reps: '', rir: null },
      { weight: '102.5', reps: '3', rir: 1 },
      { weight: '100', reps: '', rir: null },
    ])
  })
})

describe('toSetParams', () => {
  it('重量と回数の両方が入った列だけを、列の位置を番号にして返す', () => {
    const columns: SetColumn[] = [
      { weight: '102.5', reps: '5', rir: 2 },
      { weight: '102.5', reps: '', rir: null },
      { weight: '', reps: '6', rir: null },
      { weight: '0', reps: '0', rir: null },
    ]

    expect(toSetParams(columns)).toEqual([
      { order: 1, weight: 102.5, reps: 5, rir: 2 },
      { order: 4, weight: 0, reps: 0, rir: null },
    ])
  })
})

describe('copyPreviousColumn', () => {
  it('前の列の重量・回数・RIR を指定した列に入れ、ほかの列は変えない', () => {
    const columns: SetColumn[] = [
      { weight: '102.5', reps: '5', rir: 2 },
      { weight: '100', reps: '6', rir: 1 },
      EMPTY_COLUMN,
      { weight: '95', reps: '8', rir: null },
    ]

    expect(copyPreviousColumn(columns, 2)).toEqual([
      { weight: '102.5', reps: '5', rir: 2 },
      { weight: '100', reps: '6', rir: 1 },
      { weight: '100', reps: '6', rir: 1 },
      { weight: '95', reps: '8', rir: null },
    ])
  })

  it.each([
    { case: '前の列が空', previous: EMPTY_COLUMN },
    { case: '前の列に重量だけが入力されている', previous: { weight: '100', reps: '', rir: null } },
    { case: '前の列に回数だけが入力されている', previous: { weight: '', reps: '5', rir: 2 } },
  ])('$case なら、指定した列を変えない', ({ previous }) => {
    const columns: SetColumn[] = [previous, { weight: '100', reps: '6', rir: 1 }]

    expect(copyPreviousColumn(columns, 1)).toEqual([previous, { weight: '100', reps: '6', rir: 1 }])
  })

  it('前の列が存在しない先頭の列なら、列を変えない', () => {
    const columns: SetColumn[] = [{ weight: '100', reps: '6', rir: 1 }]

    expect(copyPreviousColumn(columns, 0)).toEqual(columns)
  })
})

describe('appendColumn', () => {
  it('末尾に空の列を1つ足す', () => {
    const columns: SetColumn[] = [{ weight: '102.5', reps: '5', rir: 2 }]

    expect(appendColumn(columns)).toEqual([{ weight: '102.5', reps: '5', rir: 2 }, EMPTY_COLUMN])
  })
})

describe('列を変える関数', () => {
  it.each([
    { name: 'fillWeightForward', update: (columns: SetColumn[]) => fillWeightForward(columns, 0) },
    { name: 'copyPreviousColumn', update: (columns: SetColumn[]) => copyPreviousColumn(columns, 1) },
    { name: 'appendColumn', update: appendColumn },
  ])('$name は入力の列を書き換えない', ({ update }) => {
    const columns: SetColumn[] = [{ weight: '100', reps: '5', rir: 2 }, EMPTY_COLUMN]
    const before = structuredClone(columns)

    update(columns)

    expect(columns).toEqual(before)
  })
})

describe('isValidWeight', () => {
  it.each([
    { weight: '', expected: true },
    { weight: '0', expected: true },
    { weight: '102.5', expected: true },
    { weight: '500', expected: true },
    { weight: '-0.5', expected: false },
    { weight: '500.5', expected: false },
  ])('重量 $weight は $expected', ({ weight, expected }) => {
    expect(isValidWeight(weight)).toBe(expected)
  })
})

describe('isValidReps', () => {
  it.each([
    { reps: '', expected: true },
    { reps: '0', expected: true },
    { reps: '100', expected: true },
    { reps: '-1', expected: false },
    { reps: '101', expected: false },
    { reps: '2.5', expected: false },
  ])('回数 $reps は $expected', ({ reps, expected }) => {
    expect(isValidReps(reps)).toBe(expected)
  })
})
