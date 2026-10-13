import { describe, it, expect } from 'vitest'
import { evaluateRirAnswers } from '../rir'

describe('evaluateRirAnswers', () => {
  it.each([
    { answers: [true, true, false], rir: 2, rpe: 8 },
    { answers: [false], rir: 0, rpe: 10 },
    { answers: [true, true, true], rir: 3, rpe: 7 },
  ])('回答 $answers から RIR $rir と RPE $rpe を求める', ({ answers, rir, rpe }) => {
    expect(evaluateRirAnswers(answers)).toEqual({ status: 'answered', rir, rpe })
  })
})
