import { describe, expect, it } from 'vitest'
import {
  calculateLineAxes,
  calculateNiceMax,
  calculatePeriodStart,
  scaleToHeight,
  toStepPoints,
  type PeriodPreset,
} from '@/lib/analytics'

describe('calculateNiceMax', () => {
  it.each([
    [0, 1],
    [9850, 10000],
    [112600, 120000],
    [48350, 50000],
    [7, 8],
  ])('値の最大 %d を切りのよい %d に切り上げる', (maxValue, expected) => {
    expect(calculateNiceMax(maxValue)).toBe(expected)
  })
})

describe('scaleToHeight', () => {
  it('棒の高さが値に比例する', () => {
    expect(scaleToHeight(5000, { max: 10000, height: 120 })).toBe(60)
  })
})

describe('toStepPoints', () => {
  it('トレーニングマックスの変更を、次の変更まで横に伸ばす階段状の点にする', () => {
    expect(toStepPoints([{ x: 1, y: 88 }, { x: 12, y: 90.5 }], { endX: 14 })).toEqual([
      { x: 1, y: 88 },
      { x: 12, y: 88 },
      { x: 12, y: 90.5 },
      { x: 14, y: 90.5 },
    ])
  })
})

describe('calculatePeriodStart', () => {
  it.each<[PeriodPreset, string]>([
    ['three_months', '2026-07-15'],
    ['six_months', '2026-04-15'],
    ['one_year', '2025-10-15'],
    ['all', '2000-01-01'],
  ])('%s は今日を終了日として開始日 %s から始まる', (preset, expected) => {
    expect(calculatePeriodStart(preset, '2026-10-14')).toBe(expected)
  })
})

describe('calculateLineAxes', () => {
  it.each([
    [
      'fit は y を 5 刻みで点の範囲に合わせ、上に 5 の余白を足す',
      [{ x: 10, y: 88 }, { x: 20, y: 92.8 }],
      'fit' as const,
      { xRange: { min: 10, max: 20 }, yRange: { min: 85, max: 100 }, xTicks: [10, 15, 20] },
    ],
    [
      'zero は y を 0 から切りのよい最大までにする',
      [{ x: 1, y: 1200 }, { x: 12, y: 2600 }],
      'zero' as const,
      { xRange: { min: 1, max: 12 }, yRange: { min: 0, max: 3000 }, xTicks: [1, 7, 12] },
    ],
    [
      '点が1つなら x の範囲を前後に広げ、目盛りを重ねない',
      [{ x: 5, y: 90 }],
      'fit' as const,
      { xRange: { min: 4, max: 6 }, yRange: { min: 90, max: 95 }, xTicks: [5] },
    ],
  ])('%s', (_name, points, yAxis, expected) => {
    expect(calculateLineAxes(points, { yAxis })).toEqual(expected)
  })

  it('点が無ければ軸を決めない', () => {
    expect(calculateLineAxes([], { yAxis: 'fit' })).toBeNull()
  })
})
