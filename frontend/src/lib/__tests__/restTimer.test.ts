import { describe, it, expect } from 'vitest'
import { formatRestTime, remainingRestRatio, remainingRestSeconds } from '../restTimer'

describe('formatRestTime', () => {
  it.each([
    { seconds: 0, expected: '0:00' },
    { seconds: 9, expected: '0:09' },
    { seconds: 90, expected: '1:30' },
    { seconds: 600, expected: '10:00' },
  ])('$seconds 秒を $expected と表示する', ({ seconds, expected }) => {
    expect(formatRestTime(seconds)).toBe(expected)
  })
})

describe('remainingRestSeconds', () => {
  it.each([
    { case: '終了の1秒前', endsAtMs: 10_000, nowMs: 9_000, expected: 1 },
    { case: '端数のある残り', endsAtMs: 10_000, nowMs: 8_500, expected: 2 },
    { case: '終了ちょうど', endsAtMs: 10_000, nowMs: 10_000, expected: 0 },
    { case: '終了を過ぎた時刻', endsAtMs: 10_000, nowMs: 15_000, expected: 0 },
    { case: '開始より前の時刻', endsAtMs: 100_000, nowMs: 0, expected: 90 },
  ])('$case は残り $expected 秒にする', ({ endsAtMs, nowMs, expected }) => {
    expect(remainingRestSeconds(endsAtMs, nowMs, 90)).toBe(expected)
  })
})

describe('remainingRestRatio', () => {
  it.each([
    { remainingSeconds: 90, expected: 1 },
    { remainingSeconds: 45, expected: 0.5 },
    { remainingSeconds: 0, expected: 0 },
  ])('全体 90 秒のうち残り $remainingSeconds 秒の割合は $expected', ({ remainingSeconds, expected }) => {
    expect(remainingRestRatio(remainingSeconds, 90)).toBe(expected)
  })
})
