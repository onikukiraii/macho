import { describe, it, expect } from 'vitest'
import type { BodyPart, Exercise } from '@/api/constants'
import { formatPlanned, formatSet, groupExercisesByBodyPart } from '../exercises'

function buildExercise(name: string, bodyPart: BodyPart): Exercise {
  return {
    uid: name,
    name,
    body_part: bodyPart,
    kind: 'double_progression',
    parent_uid: null,
    parent_name: null,
    coefficient: null,
    e1rm_divisor: 33.3,
    increment_kg: 2.5,
    default_rest_seconds: 90,
    current_training_max: null,
  }
}

describe('formatSet', () => {
  it.each([
    [{ order: 1, weight: 100, reps: 5, rir: null }, '100 kg × 5'],
    [{ order: 1, weight: 100, reps: 5, rir: 2 }, '100 kg × 5 RIR 2'],
    [{ exercise_name: 'ベンチプレス', weight: 77.5, reps: 5, rir: 2 }, '77.5 kg × 5 RIR 2'],
  ])('%j を %s にする', (set, expected) => {
    expect(formatSet(set)).toBe(expected)
  })
})

describe('formatPlanned', () => {
  it.each([
    {
      planned: { sets: 3, reps: 5, reps_max: 8, target_rpe: 8, target_percent: 80 },
      targetWeight: 100,
      expected: '3×5〜8 RPE8 80% / 目標 100 kg',
    },
    {
      planned: { sets: 4, reps: 5, reps_max: null, target_rpe: 7.5, target_percent: null },
      targetWeight: 75,
      expected: '4×5 RPE7.5 / 目標 75 kg',
    },
    {
      planned: { sets: 3, reps: 10, reps_max: null, target_rpe: null, target_percent: null },
      targetWeight: null,
      expected: '3×10',
    },
  ])('予定 $planned と目標重量 $targetWeight を $expected にする', ({ planned, targetWeight, expected }) => {
    expect(formatPlanned(planned, targetWeight)).toBe(expected)
  })
})

describe('groupExercisesByBodyPart', () => {
  it('胸・背中・肩・腕・脚・腹の順に並べ、部位の中は元の順を保ち、種目の無い部位は除く', () => {
    const groups = groupExercisesByBodyPart([
      buildExercise('スクワット', 'legs'),
      buildExercise('ラットプルダウン', 'back'),
      buildExercise('ベンチプレス', 'chest'),
      buildExercise('懸垂', 'back'),
    ])

    expect(groups.map((group) => [group.bodyPart, group.exercises.map((exercise) => exercise.name)])).toEqual([
      ['chest', ['ベンチプレス']],
      ['back', ['ラットプルダウン', '懸垂']],
      ['legs', ['スクワット']],
    ])
  })
})
