import { describe, it, expect } from 'vitest'
import { evaluateRirAnswers } from '../rir'

describe('evaluateRirAnswers', () => {
  it.each([
    { answers: [true, true, false], rir: 2, rpe: 8 },
    { answers: [true, false], rir: 1, rpe: 9 },
    { answers: [false], rir: 0, rpe: 10 },
    { answers: [true, true, true], rir: 3, rpe: 7 },
  ])('回答 $answers から RIR $rir と RPE $rpe を求める', ({ answers, rir, rpe }) => {
    expect(evaluateRirAnswers(answers)).toEqual({ status: 'answered', rir, rpe })
  })

  it.each([
    { answers: [], reps: 1 },
    { answers: [true, true], reps: 3 },
  ])('回答 $answers の次は、あと $reps 回の質問をする', ({ answers, reps }) => {
    expect(evaluateRirAnswers(answers)).toEqual({ status: 'asking', reps })
  })
})
