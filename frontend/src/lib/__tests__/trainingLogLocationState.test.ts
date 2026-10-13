import { describe, it, expect } from 'vitest'
import { readTrainingMaxUpdates } from '../trainingLogLocationState'

describe('readTrainingMaxUpdates', () => {
  it('記録の作成から渡されたお知らせの中身を返す', () => {
    const updates = [{ exercise_name: 'ベンチプレス', before: 88, after: 90.5 }]

    expect(readTrainingMaxUpdates({ trainingMaxUpdates: updates })).toEqual(updates)
  })

  it.each([
    { case: '遷移で何も渡されていない', state: null },
    { case: 'お知らせの中身が配列でない', state: { trainingMaxUpdates: 'ベンチプレス' } },
    { case: '更新後の値が欠けている', state: { trainingMaxUpdates: [{ exercise_name: 'ベンチプレス', before: 88 }] } },
    { case: '種目名が文字列でない', state: { trainingMaxUpdates: [{ exercise_name: 1, before: 88, after: 90.5 }] } },
  ])('$case ときは、お知らせを出さない', ({ state }) => {
    expect(readTrainingMaxUpdates(state)).toEqual([])
  })
})
