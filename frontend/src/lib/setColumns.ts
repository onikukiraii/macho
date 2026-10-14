import type { components } from '@/api/schema'

type Schemas = components['schemas']

export type SetColumn = { weight: string; reps: string; rir: number | null }

const UNPLANNED_COLUMN_COUNT = 5
const MAX_WEIGHT = 500
const MAX_REPS = 100
export const MAX_COLUMN_COUNT = 50
const EMPTY_COLUMN: SetColumn = { weight: '', reps: '', rir: null }

/** 保存済みのセットを番号の列に置き、予定のセット数か、予定外なら5つまで空の列で埋める */
export function initializeColumns(performed: Pick<Schemas['PerformedExerciseResponse'], 'planned' | 'sets'>): SetColumn[] {
  const count = Math.max(
    performed.planned?.sets ?? UNPLANNED_COLUMN_COUNT,
    ...performed.sets.map((set) => set.order),
  )
  return Array.from({ length: count }, (_, index) => {
    const set = performed.sets.find((saved) => saved.order === index + 1)
    return set === undefined ? EMPTY_COLUMN : { weight: String(set.weight), reps: String(set.reps), rir: set.rir }
  })
}

export function appendColumn(columns: SetColumn[]): SetColumn[] {
  return [...columns, EMPTY_COLUMN]
}

/** 指定した列の重量を、それより後ろで重量が空の列へコピーする */
export function fillWeightForward(columns: SetColumn[], index: number): SetColumn[] {
  const { weight } = columns[index]
  return columns.map((column, position) =>
    position > index && column.weight === '' ? { ...column, weight } : column,
  )
}

/** 前の列が存在しないか、重量か回数が空でセットと見なされないときは、入力済みの列を消さないよう何も変えない */
export function copyPreviousColumn(columns: SetColumn[], index: number): SetColumn[] {
  const previous = columns[index - 1]
  if (previous === undefined || previous.weight === '' || previous.reps === '') return columns
  return columns.map((column, position) => (position === index ? previous : column))
}

export function isValidWeight(weight: string): boolean {
  return weight === '' || (Number(weight) >= 0 && Number(weight) <= MAX_WEIGHT)
}

export function isValidReps(reps: string): boolean {
  return reps === '' || (Number.isInteger(Number(reps)) && Number(reps) >= 0 && Number(reps) <= MAX_REPS)
}

/** 重量と回数の両方が入力された列をセットにする。番号は列の位置で、途中に空の列があれば欠番になる */
export function toSetParams(columns: SetColumn[]): Schemas['SetParams'][] {
  return columns.flatMap((column, index) =>
    column.weight === '' || column.reps === ''
      ? []
      : [{ order: index + 1, weight: Number(column.weight), reps: Number(column.reps), rir: column.rir }],
  )
}
